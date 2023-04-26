"""
Test suite for addresses API
"""
import json
import uuid
from unittest import mock

import arrow
from rest_framework.pagination import PageNumberPagination

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


def get_payload(address):
    """
    According to an Address object, return a valid payload required by
    create/update address api routes.
    """
    return {
        "address": address.address,
        "city": address.city,
        "country": str(address.country),
        "first_name": address.first_name,
        "last_name": address.last_name,
        "title": address.title,
        "postcode": address.postcode,
    }


# pylint: disable=too-many-public-methods
class AddressAPITestCase(BaseAPITestCase):
    """Manage user address API test case"""

    def test_api_address_get_addresses_without_authorization(self):
        """Get user addresses not allowed without HTTP AUTH"""
        # Try to get addresses without Authorization
        response = self.client.get("/api/v1.0/addresses/")
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_address_get_addresses_with_bad_token(self):
        """Get user addresses not allowed with bad user token"""
        # Try to get addresses with bad token
        response = self.client.get(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_address_get_addresses_with_expired_token(self):
        """Get user addresses not allowed with user token expired"""
        # Try to get addresses with expired token
        token = self.get_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            "/api/v1.0/addresses/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_address_get_addresses_for_new_user(self):
        """If we try to get addresses for a user not in db, the user is not created."""
        username = "panoramix"
        token = self.get_user_token(username)

        response = self.client.get(
            "/api/v1.0/addresses/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        with self.assertNumQueries(0):
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
        self.assertFalse(models.User.objects.exists())

    def test_api_address_get_addresses(self):
        """Get addresses for a user in db with two addresses linked to him"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address1 = factories.AddressFactory.create(owner=user, title="Office")
        address2 = factories.AddressFactory.create(owner=user, title="Home")

        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1.0/addresses/", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(address.id),
                        "address": address.address,
                        "city": address.city,
                        "country": str(address.country),
                        "first_name": address.first_name,
                        "is_main": address.is_main,
                        "last_name": address.last_name,
                        "postcode": address.postcode,
                        "title": address.title,
                    }
                    for address in [address2, address1]
                ],
            },
        )

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_address_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        addresses = factories.AddressFactory.create_batch(3, owner=user)
        address_ids = [str(address.id) for address in addresses]

        response = self.client.get(
            "/api/v1.0/addresses/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"], "http://testserver/api/v1.0/addresses/?page=2"
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            address_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            "/api/v1.0/addresses/?page=2", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(content["previous"], "http://testserver/api/v1.0/addresses/")

        self.assertEqual(len(content["results"]), 1)
        address_ids.remove(content["results"][0]["id"])
        self.assertEqual(address_ids, [])

    def test_api_address_create_without_authorization(self):
        """Create/update user addresses not allowed without HTTP AUTH"""
        # Try to create address without Authorization
        address = factories.AddressFactory.build()

        response = self.client.post(
            "/api/v1.0/addresses/",
            data=get_payload(address),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_address_update_without_authorization(self):
        """Update user addresses not allowed without HTTP AUTH"""
        # Try to update address without Authorization
        user = factories.UserFactory()
        address = factories.AddressFactory(owner=user)
        new_address = factories.AddressFactory.build()

        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}",
            data=get_payload(new_address),
            follow=True,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_address_create_with_bad_token(self):
        """Create addresses not allowed with bad user token"""
        # Try to create addresses with bad token
        address = factories.AddressFactory.build()

        response = self.client.post(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=get_payload(address),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_address_update_with_bad_token(self):
        """Update addresses not allowed with bad user token"""
        # Try to update addresses with bad token
        user = factories.UserFactory()
        address = factories.AddressFactory.create(owner=user)
        new_address = factories.AddressFactory.build()

        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=get_payload(new_address),
            follow=True,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_address_create_with_expired_token(self):
        """Create user addresses not allowed with user token expired"""
        # Try to create addresses with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        address = factories.AddressFactory.build()

        response = self.client.post(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=get_payload(address),
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_address_update_with_expired_token(self):
        """Update user addresses not allowed with user token expired"""
        # Try to update addresses with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        address = factories.AddressFactory.create(owner=user)
        new_address = factories.AddressFactory.build()

        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=get_payload(new_address),
            follow=True,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_address_create_with_bad_payload(self):
        """Create user addresses with valid token but bad data"""
        username = "panoramix"
        token = self.get_user_token(username)
        address = factories.AddressFactory.build()
        bad_payload = get_payload(address).copy()
        bad_payload["country"] = "FRANCE"

        response = self.client.post(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_payload,
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(content, {"country": ['"FRANCE" is not a valid choice.']})
        self.assertFalse(models.User.objects.exists())

        del bad_payload["title"]
        bad_payload["country"] = "FR"
        response = self.client.post(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"title": ["This field is required."]})

    def test_api_address_update_with_bad_payload(self):
        """Update user addresses with valid token but bad data"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address = factories.AddressFactory.create(owner=user)
        new_address = factories.AddressFactory.build()
        payload = get_payload(new_address)

        # Put request without address id should not be allowed
        response = self.client.put(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)

        bad_payload = payload.copy()
        bad_payload["country"] = "FRANCE"

        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_payload,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(content, {"country": ['"FRANCE" is not a valid choice.']})

        del bad_payload["title"]
        bad_payload["country"] = "FR"
        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_payload,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(content, {"title": ["This field is required."]})

    def test_api_address_update_with_bad_user(self):
        """User token has to match with owner of address to update"""
        # create an address for a user
        address = factories.AddressFactory()
        new_address = factories.AddressFactory.build()
        # now use a token for an other user to update address
        token = self.get_user_token("panoramix")
        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=get_payload(new_address),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_api_address_update_to_demote_address(self):
        """
        User should not be able to demote its main address
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address = factories.AddressFactory(owner=user, is_main=True)

        payload = get_payload(address)
        payload["is_main"] = False

        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content),
            {"__all__": ["Demote a main address is forbidden"]},
        )

    def test_api_address_create_update(self):
        """Create/update user addresses with valid token and data"""
        username = "panoramix"
        token = self.get_user_token(username)
        address = factories.AddressFactory.build()
        payload = get_payload(address)

        response = self.client.post(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        # panoramix was a unknown user, so a new user was created
        owner = models.User.objects.get()
        self.assertEqual(owner.username, username)

        # new address was created for user panoramix
        address = models.Address.objects.get()
        self.assertEqual(address.owner, owner)
        self.assertEqual(address.city, payload["city"])

        # finally update address
        payload["title"] = "Office"
        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.Address.objects.count(), 1)
        address = models.Address.objects.get()
        self.assertEqual(address.title, payload["title"])
        self.assertEqual(address.owner, owner)
        self.assertEqual(address.city, payload["city"])

    def test_api_address_create_update_id_field_is_read_only(self):
        """
        When user creates/updates an address,
        it should not be allowed to set the "id" field
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address = factories.AddressFactory.build()
        # - Add an id field to the request body
        payload = get_payload(address)
        payload["id"] = uuid.uuid4()

        response = self.client.post(
            "/api/v1.0/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        # new address has been successfully created but with a generated id
        address = models.Address.objects.get()
        self.assertEqual(address.title, payload["title"])
        self.assertNotEqual(address.id, payload["id"])

        payload["id"] = uuid.uuid4()
        payload["title"] = "Work"

        response = self.client.put(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=payload,
            content_type="application/json",
        )

        # address has been successfully updated but its id not
        address = models.Address.objects.get()
        self.assertEqual(address.title, "Work")
        self.assertNotEqual(address.id, payload["id"])

    def test_api_address_delete_without_authorization(self):
        """Delete address is not allowed without authorization"""
        user = factories.UserFactory()
        address = factories.AddressFactory.create(owner=user, title="Office")
        response = self.client.delete(
            f"/api/v1.0/addresses/{address.id}/",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_address_delete_with_bad_authorization(self):
        """Delete address is not allowed with bad authorization"""
        user = factories.UserFactory()
        address = factories.AddressFactory.create(owner=user)
        response = self.client.delete(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_address_delete_with_expired_token(self):
        """Delete address is not allowed with expired token"""
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        address = factories.AddressFactory.create(owner=user)
        response = self.client.delete(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_address_delete_with_bad_user(self):
        """User token has to match with owner of address to delete"""
        # create an address for a user
        address = factories.AddressFactory()
        # now use a token for an other user to update address
        token = self.get_user_token("panoramix")
        response = self.client.delete(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_address_delete(self):
        """Delete address is allowed with valid token"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address = factories.AddressFactory.create(owner=user)
        response = self.client.delete(
            f"/api/v1.0/addresses/{address.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(models.Address.objects.exists())

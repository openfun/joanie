"""
Test suite for addresses API
"""
import json

import arrow

from joanie.core import factories, models

from .base import BaseAPITestCase

ADDRESS_DATA = {
    "name": "Home",
    "address": "10 rue Stine",
    "postcode": "75001",
    "city": "Paris",
    "country": "FR",
}


class AddressAPITestCase(BaseAPITestCase):
    """Manage user address API test case"""

    def test_get_addresses_without_authorization(self):
        """Get user addresses not allowed without HTTP AUTH"""
        # Try to get addresses without Authorization
        response = self.client.get("/api/addresses/")
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_get_addresses_with_bad_token(self):
        """Get user addresses not allowed with bad user token"""
        # Try to get addresses with bad token
        response = self.client.get(
            "/api/addresses/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_get_addresses_with_expired_token(self):
        """Get user addresses not allowed with user token expired"""
        # Try to get addresses with expired token
        token = self.get_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            "/api/addresses/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_get_addresses_for_new_user(self):
        """If we try to get addresses for a user not in db, we create a new user first"""
        username = "panoramix"
        token = self.get_user_token(username)
        response = self.client.get(
            "/api/addresses/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        addresses_data = response.data
        self.assertEqual(len(addresses_data), 0)
        self.assertEqual(models.User.objects.get(username=username).username, username)

    def test_get_addresses(self):
        """Get addresses for a user in db with two addresses linked to him"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address1 = factories.AddressFactory.create(owner=user, name="Office")
        address2 = factories.AddressFactory.create(owner=user, name="Home")
        response = self.client.get(
            "/api/addresses/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)

        addresses_data = response.data
        self.assertEqual(len(addresses_data), 2)
        self.assertEqual(addresses_data[0]["name"], "Office")
        self.assertEqual(addresses_data[0]["fullname"], address1.fullname)
        self.assertEqual(addresses_data[0]["id"], str(address1.uid))
        self.assertEqual(addresses_data[1]["name"], "Home")
        self.assertEqual(addresses_data[1]["fullname"], address2.fullname)
        self.assertEqual(addresses_data[1]["id"], str(address2.uid))

    def test_create_address_without_authorization(self):
        """Create/update user addresses not allowed without HTTP AUTH"""
        # Try to create address without Authorization
        response = self.client.post(
            "/api/addresses/",
            data=ADDRESS_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_update_address_without_authorization(self):
        """Update user addresses not allowed without HTTP AUTH"""
        # Try to update address without Authorization
        user = factories.UserFactory()
        address = factories.AddressFactory.create(owner=user)
        response = self.client.put(
            f"/api/addresses/{address.uid}",
            data=ADDRESS_DATA,
            follow=True,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_create_address_with_bad_token(self):
        """Create addresses not allowed with bad user token"""
        # Try to create addresses with bad token
        response = self.client.post(
            "/api/addresses/",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=ADDRESS_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_update_address_with_bad_token(self):
        """Update addresses not allowed with bad user token"""
        # Try to update addresses with bad token
        user = factories.UserFactory()
        address = factories.AddressFactory.create(owner=user)
        response = self.client.put(
            f"/api/addresses/{address.uid}",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=ADDRESS_DATA,
            follow=True,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_create_address_with_expired_token(self):
        """Create user addresses not allowed with user token expired"""
        # Try to create addresses with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.post(
            "/api/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=ADDRESS_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_update_address_with_expired_token(self):
        """Update user addresses not allowed with user token expired"""
        # Try to update addresses with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        address = factories.AddressFactory.create(owner=user)
        response = self.client.put(
            f"/api/addresses/{address.uid}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=ADDRESS_DATA,
            follow=True,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_create_address_with_bad_data(self):
        """Create user addresses with valid token but bad data"""
        username = "panoramix"
        token = self.get_user_token(username)
        bad_data = ADDRESS_DATA.copy()
        bad_data["country"] = "FRANCE"
        response = self.client.post(
            "/api/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_data,
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"country": ['"FRANCE" is not a valid choice.']})
        self.assertFalse(models.User.objects.exists())

        del bad_data["name"]
        bad_data["country"] = "FR"
        response = self.client.post(
            "/api/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"name": ["This field is required."]})

    def test_update_address_with_bad_data(self):
        """Update user addresses with valid token but bad data"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address = factories.AddressFactory.create(owner=user)

        # check bad request returned if address_id is missing
        response = self.client.put(
            "/api/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=ADDRESS_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        bad_data = ADDRESS_DATA.copy()
        bad_data["country"] = "FRANCE"
        response = self.client.put(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"errors": {"country": ['"FRANCE" is not a valid choice.']}}
        )

        del bad_data["name"]
        bad_data["country"] = "FR"
        response = self.client.put(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"errors": {"name": ["This field is required."]}})

    def test_update_address_with_bad_user(self):
        """User token has to match with owner of address to update"""
        # create an address for a user
        address = factories.AddressFactory()
        # now use a token for an other user to update address
        token = self.get_user_token("panoramix")
        response = self.client.put(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=ADDRESS_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_update_address(self):
        """Create/update user addresses with valid token and data"""
        username = "panoramix"
        token = self.get_user_token(username)

        response = self.client.post(
            "/api/addresses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=ADDRESS_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        # panoramix was a unknown user, so a new user was created
        owner = models.User.objects.get()
        self.assertEqual(owner.username, username)

        # new address was created for user panoramix
        address = models.Address.objects.get()
        self.assertEqual(address.owner, owner)
        self.assertEqual(address.city, "Paris")

        # finally update address
        data = ADDRESS_DATA.copy()
        data["name"] = "Office"
        response = self.client.put(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.Address.objects.count(), 1)
        address = models.Address.objects.get()
        self.assertEqual(address.name, "Office")
        self.assertEqual(address.owner, owner)
        self.assertEqual(address.city, "Paris")

    def test_delete_without_authorization(self):
        """Delete address is not allowed without authorization"""
        user = factories.UserFactory()
        address = factories.AddressFactory.create(owner=user, name="Office")
        response = self.client.delete(
            f"/api/addresses/{address.uid}/",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_with_bad_authorization(self):
        """Delete address is not allowed with bad authorization"""
        user = factories.UserFactory()
        address = factories.AddressFactory.create(owner=user)
        response = self.client.delete(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_with_expired_token(self):
        """Delete address is not allowed with expired token"""
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        address = factories.AddressFactory.create(owner=user)
        response = self.client.delete(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_address_with_bad_user(self):
        """User token has to match with owner of address to delete"""
        # create an address for a user
        address = factories.AddressFactory()
        # now use a token for an other user to update address
        token = self.get_user_token("panoramix")
        response = self.client.delete(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_address(self):
        """Delete address is allowed with valid token"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        address = factories.AddressFactory.create(owner=user)
        response = self.client.delete(
            f"/api/addresses/{address.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(models.Address.objects.exists())

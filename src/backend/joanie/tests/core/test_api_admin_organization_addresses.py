"""
Test suite for Organization Address Admin API endpoints.
"""

import uuid
from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories


class OrganizationAddressAdminAPITest(TestCase):
    """
    Test suite for Organization Address Admin API endpoints.
    """

    def test_admin_api_organization_addresses_request_anonymous(self):
        """
        Anonymous users should not be able to request organization addresses endpoint.
        """
        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/addresses/"
        )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    def test_admin_api_organization_addresses_request_authenticated(self):
        """
        Authenticated users should not be able to request organization addresses endpoint.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/addresses/"
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    def test_admin_api_organization_addresses_request_list(self):
        """
        Super admin user should not be able to list organization addresses.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/addresses/"
        )

        self.assertContains(
            response,
            'Method \\"GET\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_admin_api_organization_addresses_request_get(self):
        """
        Super admin user should not be able to retrieve an organization address.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        address = factories.OrganizationAddressFactory(organization=organization)

        response = self.client.get(
            f"/api/v1.0/admin/organizations/{organization.id}/addresses/{address.id}/"
        )

        self.assertContains(
            response,
            'Method \\"GET\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_admin_api_organization_addresses_request_create(self):
        """
        Super admin user should be able to create an address for an organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        organization = factories.OrganizationFactory()
        self.client.login(username=admin.username, password="password")

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{organization.id}/addresses/",
            data={
                "address": "1 rue de l'exemple",
                "city": "Paris",
                "country": "FR",
                "first_name": "John",
                "last_name": "Doe",
                "is_main": True,
                "is_reusable": True,
                "postcode": "75000",
                "title": "Home",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(organization.addresses.count(), 1)

        organization_address = organization.addresses.first()

        content = response.json()
        self.assertEqual(
            content,
            {
                "id": str(organization_address.id),
                "address": str(organization_address.address),
                "city": str(organization_address.city),
                "country": str(organization_address.country),
                "first_name": (organization_address.first_name),
                "last_name": (organization_address.last_name),
                "is_main": (organization_address.is_main),
                "is_reusable": (organization_address.is_reusable),
                "postcode": (organization_address.postcode),
                "title": (organization_address.title),
            },
        )

    def test_admin_api_organization_addresses_request_create_with_unknown_organization_id(
        self,
    ):
        """
        An 400 Bad Request should be raised if the organization id is unknown.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        not_exiting_organization_id = uuid.uuid4()

        response = self.client.post(
            f"/api/v1.0/admin/organizations/{not_exiting_organization_id}/addresses/",
            data={
                "address": "1 rue de l'exemple",
                "city": "Paris",
                "country": "FR",
                "first_name": "John",
                "last_name": "Doe",
                "is_main": True,
                "is_reusable": True,
                "postcode": "75000",
                "title": "Home",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(), {"organization_id": "Resource does not exist."}
        )

    def test_admin_api_organization_addresses_request_update(self):
        """
        Super admin user should be able to update an organization address.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        address = factories.OrganizationAddressFactory(
            address="1 rue de l'exemple", organization=organization
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/addresses/{address.id}/",
            content_type="application/json",
            data={
                "address": "61 bis rue de l'exemple",
                "city": "Paris",
                "country": "FR",
                "first_name": "John",
                "last_name": "Doe",
                "is_main": True,
                "is_reusable": True,
                "postcode": "75000",
                "title": "Home",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "id": str(address.id),
                "address": "61 bis rue de l'exemple",
                "city": "Paris",
                "country": "FR",
                "first_name": "John",
                "last_name": "Doe",
                "is_main": True,
                "is_reusable": True,
                "postcode": "75000",
                "title": "Home",
            },
        )

    def test_admin_api_organization_addresses_request_update_with_unknown_address_id(
        self,
    ):
        """
        An 404 Not found error should be raised if the address id to update is unknown.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()

        self.assertEqual(organization.addresses.count(), 0)

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/addresses/{uuid.uuid4()}/",
            data={
                "address": "61 bis rue de l'exemple",
                "city": "Paris",
                "country": "FR",
                "first_name": "John",
                "last_name": "Doe",
                "is_main": True,
                "is_reusable": True,
                "postcode": "75000",
                "title": "Home",
            },
        )

        self.assertContains(
            response,
            "No Address matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_admin_api_organization_addresses_request_update_with_partial_payload(self):
        """
        An 400 Bad request error should be raised if a partial payload is provided.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        address = factories.OrganizationAddressFactory(
            organization=organization, title="Office"
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/accesses/{address.id}/",
            content_type="application/json",
            data={
                "title": "Home",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            response.json(),
            {"detail": "No OrganizationAccess matches the given query."},
        )

    def test_admin_api_organization_addresses_request_update_with_fake_organization_id(
        self,
    ):
        """
        An 400 Bad request error should be raised if trying to update an address with a
        non existing `organization_id`.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        address = factories.OrganizationAddressFactory(
            organization=organization, title="Office"
        )

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{uuid.uuid4()}/addresses/{address.id}/",
            content_type="application/json",
            data={
                "address": "61 bis rue de l'exemple",
                "city": "Paris",
                "country": "FR",
                "first_name": "John",
                "last_name": "Doe",
                "is_main": True,
                "is_reusable": True,
                "postcode": "75000",
                "title": "Home",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "detail": "The relation does not exist between the address and the organization."
            },
        )

    def test_admin_api_organization_addresses_request_partial_update(self):
        """
        Super admin user should be able to partially update an organization's address because it
        accepts that needs to be applied.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        address = factories.OrganizationAddressFactory(
            title="Headquarters",
            address="61 bis rue de l'exemple",
            city="Paris",
            country="FR",
            first_name="John",
            last_name="Doe",
            is_main=True,
            is_reusable=True,
            postcode="75000",
        )

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{address.organization.id}/addresses/{address.id}/",
            content_type="application/json",
            data={
                "title": "Home sweet home",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(address.id),
                "title": "Home sweet home",
                "address": "61 bis rue de l'exemple",
                "city": "Paris",
                "country": "FR",
                "first_name": "John",
                "last_name": "Doe",
                "is_main": True,
                "is_reusable": True,
                "postcode": "75000",
            },
        )

    def test_admin_api_organization_addresses_request_delete(self):
        """
        Super admin user should be able to delete an organization's address when the relation
        exists.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        address = factories.OrganizationAddressFactory()

        self.assertEqual(address.organization.addresses.count(), 1)

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{address.organization.id}/addresses/{address.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(address.organization.accesses.count(), 0)

    def test_admin_api_organization_addresses_request_delete_with_wrong_address_id(
        self,
    ):
        """
        Super admin user should not be able to delete an address if there is no relation
        between the organization and the address.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        [organization_1, organization_2] = factories.OrganizationFactory.create_batch(2)
        address = factories.OrganizationAddressFactory(organization=organization_1)

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{organization_2.id}/addresses/{address.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            ["The relation does not exist between the address and the organization."],
        )

    def test_admin_api_organization_addresses_request_update_with_wrong_address_id(
        self,
    ):
        """
        Super admin user should not be able to update partially an address if there is no relation
        between the organization and the address.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        [organization_1, organization_2] = factories.OrganizationFactory.create_batch(2)
        address = factories.OrganizationAddressFactory(organization=organization_1)

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization_2.id}/addresses/{address.id}/",
            content_type="application/json",
            data={"title": "Office"},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "detail": "The relation does not exist between the address and the organization."
            },
        )

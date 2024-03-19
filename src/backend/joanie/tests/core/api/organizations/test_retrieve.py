"""
Test suite for Organization retrieve API endpoint.
"""

from http import HTTPStatus
from unittest import mock

from joanie.core import factories
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class OrganizationApiRetrieveTest(BaseAPITestCase):
    """
    Test suite for Organization retrieve API endpoints.
    """

    def test_api_organization_retrieve_anonymous(self):
        """
        Anonymous users should not be allowed to get an organization through its id.
        """
        organization = factories.OrganizationFactory()

        response = self.client.get(f"/api/v1.0/organizations/{organization.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organization_retrieve_authenticated_no_access(self):
        """
        Authenticated users should not be able to get an organization through its id
        if they have no access to it.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            response.json(), {"detail": "No Organization matches the given query."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organization_retrieve_authenticated_with_access(self, _):
        """
        Authenticated users should be able to get an organization through its id
        if they have access to it.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)
        address_organization = factories.OrganizationAddressFactory(
            organization=organization, is_main=True, is_reusable=True
        )
        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertTrue(content.pop("abilities")["get"])
        self.assertEqual(
            content,
            {
                "code": organization.code,
                "id": str(organization.id),
                "logo": "_this_field_is_mocked",
                "title": organization.title,
                "enterprise_code": organization.enterprise_code,
                "activity_category_code": (organization.activity_category_code),
                "contact_email": organization.contact_email,
                "contact_phone": organization.contact_phone,
                "dpo_email": organization.dpo_email,
                "address": {
                    "id": str(address_organization.id),
                    "address": address_organization.address,
                    "city": address_organization.city,
                    "postcode": address_organization.postcode,
                    "country": address_organization.country,
                    "first_name": address_organization.first_name,
                    "last_name": address_organization.last_name,
                    "title": address_organization.title,
                    "is_main": True,
                },
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organization_retrieve_when_organization_has_no_main_address(self, _):
        """
        Authenticated users should not be able to see the address of the organization
        if the address is not main and not reusable.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)
        factories.OrganizationAddressFactory(
            organization=organization, is_main=False, is_reusable=False
        )
        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertTrue(content.pop("abilities")["get"])
        self.assertEqual(
            content,
            {
                "code": organization.code,
                "id": str(organization.id),
                "logo": "_this_field_is_mocked",
                "title": organization.title,
                "address": None,
                "enterprise_code": organization.enterprise_code,
                "activity_category_code": (organization.activity_category_code),
                "contact_email": organization.contact_email,
                "contact_phone": organization.contact_phone,
                "dpo_email": organization.dpo_email,
            },
        )

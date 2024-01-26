"""
Test suite for Organization update API endpoint.
"""
import random
from http import HTTPStatus

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class OrganizationApiUpdateTest(BaseAPITestCase):
    """
    Test suite for Organization update API endpoint.
    """

    def test_api_organization_update_anonymous(self):
        """
        Anonymous users should not be able to update an organization.
        """
        organization = factories.OrganizationFactory()

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/", data=data
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

    def test_api_organization_update_authenticated_no_access(self):
        """
        Authenticated users should not be able to update an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

    def test_api_organization_update_authenticated_with_access(self):
        """
        Authenticated users with owner role should not be
        able to update an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=enums.OWNER,
        )

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

"""
Test suite for Organization Create API endpoint.
"""
import random
from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiCreateTest(BaseAPITestCase):
    """
    Test suite for Organization create API endpoint.
    """

    def test_api_organization_create_anonymous(self):
        """
        Anonymous users should not be able to create an organization.
        """
        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post("/api/v1.0/organizations/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(models.Organization.objects.exists())

    def test_api_organization_create_authenticated(self):
        """
        Authenticated users should not be able to create an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post(
            "/api/v1.0/organizations/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertFalse(models.Organization.objects.exists())

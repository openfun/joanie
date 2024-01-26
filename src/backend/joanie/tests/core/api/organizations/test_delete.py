"""
Test suite for Organization delete API endpoint.
"""
import random
from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiDeleteTest(BaseAPITestCase):
    """
    Test suite for Organization delete API endpoint.
    """

    def test_api_organization_delete_anonymous(self):
        """
        Anonymous users should not be able to delete an organization.
        """
        organization = factories.OrganizationFactory()

        response = self.client.delete(f"/api/v1.0/organizations/{organization.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(models.Organization.objects.count(), 1)

    def test_api_organization_delete_authenticated_no_access(self):
        """
        Authenticated users should not be able to delete an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(models.Organization.objects.count(), 1)

    def test_api_organization_delete_authenticated_with_access(self):
        """
        Authenticated users with owner role should not be able
        to delete an organization.
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

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(models.Organization.objects.count(), 1)

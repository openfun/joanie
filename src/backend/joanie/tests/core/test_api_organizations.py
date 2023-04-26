"""
Test suite for Organization API endpoint.
"""
import random
from unittest import mock

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiTest(BaseAPITestCase):
    """
    Test suite for Organization API endpoint.
    """

    def test_api_organization_list_anonymous(self):
        """
        Anonymous users should not be able to list organizations.
        """
        factories.OrganizationFactory()
        response = self.client.get("/api/v1.0/organizations/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organization_list_authenticated_queries(self):
        """
        Authenticated users should only see the organizations to which they have access.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        factories.OrganizationFactory()
        organizations = factories.OrganizationFactory.create_batch(3)
        factories.UserOrganizationAccessFactory(
            user=user, organization=organizations[0]
        )
        factories.UserOrganizationAccessFactory(
            user=user, organization=organizations[1]
        )

        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1.0/organizations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 2)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(organization.id) for organization in organizations[:2]],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    def test_api_organization_list_authenticated_format(self):
        """
        Authenticated users should only see the organizations to which they have access.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        factories.OrganizationFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        with mock.patch.object(
            models.Organization, "get_abilities", return_value={"foo": "bar"}
        ) as mock_abilities:
            response = self.client.get(
                "/api/v1.0/organizations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
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
                        "abilities": {"foo": "bar"},
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": {
                            "filename": organization.logo.name,
                            "height": 1,
                            "url": f"http://testserver{organization.logo.url}",
                            "width": 1,
                        },
                        "title": organization.title,
                    }
                ],
            },
        )
        self.assertEqual(mock_abilities.call_args_list[0][1]["user"], user)
        self.assertEqual(str(mock_abilities.call_args_list[0][1]["auth"]), str(token))

    def test_api_organization_get_anonymous(self):
        """
        Anonymous users should not be allowed to get an organization through its id.
        """
        organization = factories.OrganizationFactory()

        response = self.client.get(f"/api/v1.0/organizations/{organization.id}/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organization_get_authenticated_no_access(self):
        """
        Authenticated users should not be able to get an organization through its id
        if they have no access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_api_organization_get_authenticated_with_access(self):
        """
        Authenticated users should be able to get an organization through its id
        if they have access to it.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertTrue(content.pop("abilities")["get"])
        self.assertEqual(
            content,
            {
                "code": organization.code,
                "id": str(organization.id),
                "logo": {
                    "filename": organization.logo.name,
                    "height": 1,
                    "url": f"http://testserver{organization.logo.url}",
                    "width": 1,
                },
                "title": organization.title,
            },
        )

    def test_api_organization_create_anonymous(self):
        """
        Anonymous users should not be able to create an organization.
        """
        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post("/api/v1.0/organizations/", data=data)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(models.Organization.objects.exists())

    def test_api_organization_create_authenticated(self):
        """
        Authenticated users should not be able to create an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post(
            "/api/v1.0/organizations/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertFalse(models.Organization.objects.exists())

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

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

    def test_api_organization_update_authenticated(self):
        """
        Authenticated users should be able to update an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

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

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

    def test_api_organization_delete_anonymous(self):
        """
        Anonymous users should not be able to delete an organization.
        """
        organization = factories.OrganizationFactory()

        response = self.client.delete(f"/api/v1.0/organizations/{organization.id}/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(models.Organization.objects.count(), 1)

    def test_api_organization_delete_authenticated(self):
        """
        Authenticated users should not be able to delete an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Organization.objects.count(), 1)

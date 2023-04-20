"""
Test suite for Organization Admin API.
"""
import random
import re

import factory.django
from django.core.files.base import ContentFile
from django.test import TestCase

from joanie.core import factories


class OrganizationAdminApiTest(TestCase):
    """
    Test suite for Organization Admin API.
    """

    def test_admin_api_organization_request_without_authentication(self):
        """
        Anonymous users should not be able to request organizations endpoint.
        """
        response = self.client.get("/api/v1.0/admin/organizations/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_organization_request_with_lambda_user(self):
        """
        Lambda user should not be able to request organizations endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/organizations/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_organization_request_with_staff_user(self):
        """
        Staff user with basic permissions could read resource
        but not create, update, patch or delete it.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/v1.0/admin/organizations/abc/")
        self.assertEqual(response.status_code, 404)

        response = self.client.post("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, 403)

        response = self.client.put("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, 403)

        response = self.client.patch("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, 403)

        response = self.client.delete("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, 403)

    def test_admin_api_organization_list(self):
        """
        Staff user should be able to get a paginated list of organizations
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization_count = random.randint(1, 10)
        factories.OrganizationFactory.create_batch(organization_count)

        response = self.client.get("/api/v1.0/admin/organizations/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], organization_count)

    def test_admin_api_organization_list_filtered_by_search(self):
        """
        Staff user should be able to get a paginated list of organizations filtered
        through a search text
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization_count = random.randint(1, 10)
        items = factories.OrganizationFactory.create_batch(organization_count)

        response = self.client.get("/api/v1.0/admin/organizations/?search=")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], organization_count)

        response = self.client.get(
            f"/api/v1.0/admin/organizations/?search={items[0].title}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)

        response = self.client.get(
            f"/api/v1.0/admin/organizations/?search={items[0].code}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)

        organization_1 = items[0]
        self.assertEqual(
            content,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(organization_1.id),
                        "code": organization_1.code,
                        "title": organization_1.title,
                        "representative": organization_1.representative,
                        "signature": {
                            "url": f"http://testserver{organization_1.signature.url}",
                            "height": organization_1.signature.height,
                            "width": organization_1.signature.width,
                            "filename": organization_1.signature.name,
                        },
                        "logo": {
                            "url": f"http://testserver{organization_1.logo.url}",
                            "height": organization_1.logo.height,
                            "width": organization_1.logo.width,
                            "filename": organization_1.logo.name,
                        },
                    }
                ],
            },
        )

    def test_admin_api_organization_list_filtered_by_search_language(self):
        """
        Staff user should be able to get a paginated list of organizations
        filtered through a search text and different languages
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        item = factories.OrganizationFactory(code="Panchnat", title="Nathan Corp")
        item.translations.create(language_code="fr-fr", title="Nathan society")

        response = self.client.get("/api/v1.0/admin/organizations/?search=pan")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "University")

        response = self.client.get(
            "/api/v1.0/admin/organizations/?search=Université",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Université")

        response = self.client.get(
            "/api/v1.0/admin/organizations/?search=university",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Université")

    def test_admin_api_organization_get(self):
        """
        Staff user should be able to get an organization through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()

        response = self.client.get(f"/api/v1.0/admin/organizations/{organization.id}/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(organization.id))
        self.assertEqual(
            content["logo"],
            {
                "url": f"http://testserver{organization.logo.url}",
                "height": 1,
                "width": 1,
                "filename": organization.logo.name,
            },
        )

    def test_admin_api_organization_create(self):
        """
        Staff user should be able to create an organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        logo = ContentFile(
            factory.django.ImageField()._make_data(  # pylint: disable=protected-access
                {"format": "png", "width": 1, "height": 1}
            ),
            name="logo.png",
        )
        data = {
            "code": "ORG-001",
            "title": "Organization 001",
            "logo": logo,
        }

        response = self.client.post("/api/v1.0/admin/organizations/", data=data)

        self.assertEqual(response.status_code, 201)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["code"], "ORG-001")
        # Logo has been uploaded successfully to media storage
        self.assertEqual(content["logo"]["height"], 1)
        self.assertEqual(content["logo"]["width"], 1)
        self.assertIsNotNone(re.search(r"^logo_.*\.png$", content["logo"]["filename"]))
        self.assertIsNotNone(
            re.search(
                r"^http:\/\/testserver\/media\/logo_.*\.png$", content["logo"]["url"]
            )
        )

    def test_admin_api_organization_update(self):
        """
        Staff user should be able to update an organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory(code="ORG-001")
        payload = {
            "code": "UPDATED-ORG-001",
            "title": "Updated Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/admin/organizations/{organization.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(organization.id))
        self.assertEqual(content["code"], "UPDATED-ORG-001")
        self.assertEqual(content["title"], "Updated Organization 001")

    def test_admin_api_organization_partially_update(self):
        """
        Staff user should be able to partially update an organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory(
            code="ORG-001", title="Organization 001"
        )

        response = self.client.patch(
            f"/api/v1.0/admin/organizations/{organization.id}/",
            content_type="application/json",
            data={"title": "Updated Organization 001"},
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(organization.id))
        self.assertEqual(content["title"], "Updated Organization 001")

    def test_admin_api_organization_delete(self):
        """
        Staff user should be able to delete an organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/organizations/{organization.id}/"
        )

        self.assertEqual(response.status_code, 204)

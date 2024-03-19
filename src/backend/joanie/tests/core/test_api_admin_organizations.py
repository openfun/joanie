"""
Test suite for Organization Admin API.
"""

import random
import re
from http import HTTPStatus
from unittest import mock

from django.core.files.base import ContentFile
from django.test import TestCase

import factory.django

from joanie.core import factories
from joanie.core.serializers import fields


class OrganizationAdminApiTest(TestCase):
    """
    Test suite for Organization Admin API.
    """

    def test_admin_api_organization_request_without_authentication(self):
        """
        Anonymous users should not be able to request organizations endpoint.
        """
        response = self.client.get("/api/v1.0/admin/organizations/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
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

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
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
        self.assertEqual(response.status_code, HTTPStatus.OK)

        response = self.client.get("/api/v1.0/admin/organizations/abc/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        response = self.client.post("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        response = self.client.put("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        response = self.client.patch("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        response = self.client.delete("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_admin_api_organization_list(self):
        """
        Staff user should be able to get a paginated list of organizations with limited
        information
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization_count = random.randint(1, 10)
        organizations = factories.OrganizationFactory.create_batch(organization_count)

        response = self.client.get("/api/v1.0/admin/organizations/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertCountEqual(
            response.json(),
            {
                "count": organization_count,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(organization.id),
                        "code": organization.code,
                        "title": organization.title,
                    }
                    for organization in organizations
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_organization_list_filter_by_query(self, _):
        """
        Staff user should be able to get a paginated list of organizations filtered
        through a search text
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization_count = random.randint(1, 10)
        [organization, *_] = factories.OrganizationFactory.create_batch(
            organization_count
        )

        response = self.client.get("/api/v1.0/admin/organizations/?query=")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], organization_count)

        response = self.client.get(
            f"/api/v1.0/admin/organizations/?query={organization.title}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)

        response = self.client.get(
            f"/api/v1.0/admin/organizations/?query={organization.code}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)

        self.assertEqual(
            content,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(organization.id),
                        "code": organization.code,
                        "title": organization.title,
                    }
                ],
            },
        )

    def test_admin_api_organization_list_filter_by_query_language(self):
        """
        Staff user should be able to get a paginated list of organizations
        filtered through a search text and different languages
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        item = factories.OrganizationFactory(code="Univ", title="University")
        item.translations.create(language_code="fr-fr", title="Université")

        response = self.client.get("/api/v1.0/admin/organizations/?query=Uni")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "University")

        response = self.client.get(
            "/api/v1.0/admin/organizations/?query=Université",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Université")

        response = self.client.get(
            "/api/v1.0/admin/organizations/?query=university",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Université")

    def test_admin_api_organization_list_filter_by_id(self):
        """
        Staff user should be able to get a paginated list of organizations
        filtered an id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organizations = factories.OrganizationFactory.create_batch(3)

        response = self.client.get("/api/v1.0/admin/organizations/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        response = self.client.get(
            f"/api/v1.0/admin/organizations/?ids={organizations[0].id}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(organizations[0].id))

        response = self.client.get(
            f"/api/v1.0/admin/organizations/?ids={organizations[0].id}&ids={organizations[1].id}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(organizations[1].id))
        self.assertEqual(content["results"][1]["id"], str(organizations[0].id))

    def test_admin_api_organization_get(self):
        """
        Staff user should be able to get an organization through its id with detailed
        information.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        # Add addresses to organization
        address = factories.OrganizationAddressFactory(organization=organization)
        # Add accesses to organization
        accesses_count = random.randint(0, 5)
        factories.UserOrganizationAccessFactory.create_batch(
            accesses_count, organization=organization
        )

        response = self.client.get(f"/api/v1.0/admin/organizations/{organization.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        assert (
            response.json()
            == {
                "id": str(organization.id),
                "code": organization.code,
                "country": organization.country,
                "title": organization.title,
                "representative": organization.representative,
                "signature": {
                    "src": f"http://testserver{organization.signature.url}",
                    "height": organization.signature.height,
                    "size": 69,
                    "width": organization.signature.width,
                    "filename": organization.signature.name,
                },
                "logo": {
                    "src": f"http://testserver{organization.logo.url}.1x1_q85.webp",
                    "height": 1,
                    "width": 1,
                    "size": organization.logo.size,
                    "srcset": (
                        f"http://testserver{organization.logo.url}.1024x1024_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "1024w, "
                        f"http://testserver{organization.logo.url}.512x512_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "512w, "
                        f"http://testserver{organization.logo.url}.256x256_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "256w, "
                        f"http://testserver{organization.logo.url}.128x128_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "128w"
                    ),
                    "filename": organization.logo.name,
                },
                "enterprise_code": organization.enterprise_code,
                "activity_category_code": organization.activity_category_code,
                "representative_profession": organization.representative_profession,
                "signatory_representative": organization.signatory_representative,
                "signatory_representative_profession": (
                    organization.signatory_representative_profession
                ),
                "contact_phone": organization.contact_phone,
                "contact_email": organization.contact_email,
                "dpo_email": organization.dpo_email,
                "addresses": [
                    {
                        "id": str(address.id),
                        "title": address.title,
                        "address": address.address,
                        "city": address.city,
                        "country": address.country,
                        "first_name": address.first_name,
                        "last_name": address.last_name,
                        "is_main": address.is_main,
                        "is_reusable": address.is_reusable,
                        "postcode": address.postcode,
                    }
                ],
                "accesses": [
                    {
                        "id": str(access.id),
                        "user": {
                            "id": str(access.user.id),
                            "username": access.user.username,
                            "full_name": access.user.get_full_name(),
                            "email": access.user.email,
                        },
                        "role": access.role,
                    }
                    for access in organization.accesses.all()
                ],
            }
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

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["code"], "ORG-001")
        # Logo has been uploaded successfully to media storage
        self.assertEqual(content["logo"]["height"], 1)
        self.assertEqual(content["logo"]["width"], 1)
        self.assertIsNotNone(re.search(r"^logo_.*\.png$", content["logo"]["filename"]))
        self.assertIsNotNone(
            re.search(
                r"^http:\/\/testserver\/media\/logo_.*\.webp$", content["logo"]["src"]
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

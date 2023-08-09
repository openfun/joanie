"""
Test suite for Certificate definition Admin API.
"""
import random

from django.test import TestCase

from joanie.core import factories


class CertificateDefinitionAdminApiTest(TestCase):
    """
    Test suite for Certificate definition Admin API.
    """

    def test_admin_api_certificate_definition_request_without_authentication(self):
        """
        Anonymous users should not be able to request certificate definition endpoint.
        """
        response = self.client.get("/api/v1.0/admin/certificate-definitions/")

        self.assertEqual(response.status_code, 401)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_certificate_definition_request_with_lambda_user(self):
        """
        Lambda user should not be able to request certificate definition endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/certificate-definitions/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_certificate_definition_list(self):
        """
        Staff user should be able to get a paginated list of certificate definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        certification_definitions_count = random.randint(1, 10)
        factories.CertificateDefinitionFactory.create_batch(
            certification_definitions_count
        )

        response = self.client.get("/api/v1.0/admin/certificate-definitions/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], certification_definitions_count)

    def test_admin_api_certificate_definition_list_filter_by_query(self):
        """
        Staff user should be able to get a paginated list of certificates definitions filtered
        through a search text
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        certification_definitions_count = random.randint(1, 10)
        items = factories.CertificateDefinitionFactory.create_batch(
            certification_definitions_count
        )

        response = self.client.get("/api/v1.0/admin/certificate-definitions/?query=")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], certification_definitions_count)

        response = self.client.get(
            f"/api/v1.0/admin/certificate-definitions/?query={items[0].title}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)

        response = self.client.get(
            f"/api/v1.0/admin/certificate-definitions/?query={items[0].name}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)

        certification_definition_1 = items[0]
        self.assertEqual(
            content,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(certification_definition_1.id),
                        "name": certification_definition_1.name,
                        "title": certification_definition_1.title,
                        "description": certification_definition_1.description,
                        "template": certification_definition_1.template,
                    }
                ],
            },
        )

    def test_admin_api_certificate_definition_list_filter_by_query_language(self):
        """
        Staff user should be able to get a paginated list of certificates definitions
        filtered through a search text and with different languages
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        item = factories.CertificateDefinitionFactory(title="Certificate 1")
        item.translations.create(language_code="fr-fr", title="Certificat 1")

        response = self.client.get(
            "/api/v1.0/admin/certificate-definitions/?query=Certificate 1"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Certificate 1")

        response = self.client.get(
            "/api/v1.0/admin/certificate-definitions/?query=Certificat 1",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Certificat 1")

        response = self.client.get(
            "/api/v1.0/admin/certificate-definitions/?query=Certificate 1",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Certificat 1")

    def test_admin_api_certificate_definition_get(self):
        """
        Staff user should be able to get a certificate definition through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        certification_definition = factories.CertificateDefinitionFactory()

        response = self.client.get(
            f"/api/v1.0/admin/certificate-definitions/{certification_definition.id}/"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(certification_definition.id))

    def test_admin_api_certificate_definition_create(self):
        """
        Staff user should be able to create a certificate definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "name": "Certificate Definition 001",
            "title": "Certificate grade 1",
            "template": "joanie.core.templates.certificate-001",
        }

        response = self.client.post(
            "/api/v1.0/admin/certificate-definitions/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, 201)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["name"], "Certificate Definition 001")

    def test_admin_api_certificate_definition_update(self):
        """
        Staff user should be able to update a certificate definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        certification_definition = factories.CertificateDefinitionFactory(
            name="Certificate Definition 001",
            title="Certificate grade 1",
            template="joanie.core.templates.certificate-001",
        )
        payload = {
            "name": "Updated Certificate Definition 001",
            "title": "Updated Certificate grade 1",
            "template": "joanie.core.templates.updated-certificate-001",
        }

        response = self.client.put(
            f"/api/v1.0/admin/certificate-definitions/{certification_definition.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(certification_definition.id))
        self.assertEqual(content["name"], "Updated Certificate Definition 001")
        self.assertEqual(content["title"], "Updated Certificate grade 1")
        self.assertEqual(
            content["template"], "joanie.core.templates.updated-certificate-001"
        )

    def test_admin_api_certificate_definition_partially_update(self):
        """
        Staff user should be able to partially update a certification_definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        certification_definition = factories.CertificateDefinitionFactory(
            template="joanie.core.templates.certificate-001",
        )

        response = self.client.patch(
            f"/api/v1.0/admin/certificate-definitions/{certification_definition.id}/",
            content_type="application/json",
            data={"template": "joanie.core.templates.updated-certificate-001"},
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(certification_definition.id))
        self.assertEqual(
            content["template"], "joanie.core.templates.updated-certificate-001"
        )

    def test_admin_api_certificate_definition_delete(self):
        """
        Staff user should be able to delete a certificate definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        certificate_definition = factories.CertificateDefinitionFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/certificate-definitions/{certificate_definition.id}/"
        )

        self.assertEqual(response.status_code, 204)

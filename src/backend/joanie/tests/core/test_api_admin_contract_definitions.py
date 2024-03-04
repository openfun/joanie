"""
Test suite for Contract definition Admin API.
"""

import random
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase, override_settings

from joanie.core import enums, factories, models


class ContractDefinitionAdminApiTest(TestCase):
    """
    Test suite for Contract definition Admin API.
    """

    maxDiff = None

    def test_admin_api_contract_definition_request_without_authentication(self):
        """
        Anonymous users should not be able to request contract definition endpoint.
        """
        response = self.client.get("/api/v1.0/admin/contract-definitions/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_contract_definition_request_with_lambda_user(self):
        """
        Lambda user should not be able to request contract definition endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/contract-definitions/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_contract_definition_list(self):
        """
        Staff user should be able to get a paginated list of contract definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definitions_count = random.randint(1, 10)
        factories.ContractDefinitionFactory.create_batch(contract_definitions_count)

        response = self.client.get("/api/v1.0/admin/contract-definitions/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], contract_definitions_count)

    def test_admin_api_contract_definition_list_filter_by_query(self):
        """
        Staff user should be able to get a paginated list of contract definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definitions_count = random.randint(1, 10)
        items = factories.ContractDefinitionFactory.create_batch(
            contract_definitions_count
        )
        contract_definition_1 = items[0]

        response = self.client.get(
            f"/api/v1.0/admin/contract-definitions/?query={contract_definition_1.title}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "body": contract_definition_1.body,
                        "description": contract_definition_1.description,
                        "id": str(contract_definition_1.id),
                        "language": contract_definition_1.language,
                        "name": contract_definition_1.name,
                        "title": contract_definition_1.title,
                    }
                ],
            },
        )

    @override_settings(LANGUAGES=(("fr-fr", "French"), ("en-us", "English")))
    def test_admin_api_contract_definition_list_filter_by_language(self):
        """
        Staff user should be able to get a paginated list of contract definition
        filtered by language.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create one contract definition per language
        for [language, _] in settings.LANGUAGES:
            factories.ContractDefinitionFactory(language=language)

        # Filter contract definition by each language
        for [language, _] in settings.LANGUAGES:
            response = self.client.get(
                f"/api/v1.0/admin/contract-definitions/?language={language}"
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["language"], language)

    def test_admin_api_contract_definition_list_filter_by_language_invalid(self):
        """
        Staff user should be able to get a paginated list of contract definition
        filtered by language but if an invalid value is provided, an error should be
        returned.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create one contract definition per language
        for [language, _] in settings.LANGUAGES:
            factories.ContractDefinitionFactory(language=language)

        response = self.client.get(
            "/api/v1.0/admin/contract-definitions/?language=invalid"
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        content = response.json()
        self.assertEqual(
            content,
            {
                "language": [
                    "Select a valid choice. invalid is not one of the available choices."
                ]
            },
        )

    def test_admin_api_contract_definition_get(self):
        """
        Staff user should be able to get a contract definition through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definition = factories.ContractDefinitionFactory()

        response = self.client.get(
            f"/api/v1.0/admin/contract-definitions/{contract_definition.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "body": contract_definition.body,
                "description": contract_definition.description,
                "id": str(contract_definition.id),
                "language": contract_definition.language,
                "name": "contract_definition",
                "title": contract_definition.title,
            },
        )

    def test_admin_api_contract_definition_create(self):
        """
        Staff user should be able to create a contract definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "title": "Contract 001",
            "template": "joanie.core.templates.contract-001",
            "language": "fr-fr",
        }

        response = self.client.post(
            "/api/v1.0/admin/contract-definitions/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Contract 001")

    def test_admin_api_contract_definition_update(self):
        """
        Staff user should be able to update a contract definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definition = factories.ContractDefinitionFactory(
            title="Contract grade 1", name=enums.CONTRACT_NAME_CHOICES[0][0]
        )
        payload = {
            "title": "Updated Contract grade 1",
            "name": enums.CONTRACT_NAME_CHOICES[0][0],
            "language": "fr-fr",
        }

        response = self.client.put(
            f"/api/v1.0/admin/contract-definitions/{contract_definition.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(contract_definition.id))
        self.assertEqual(content["title"], "Updated Contract grade 1")
        self.assertEqual(content["name"], "contract_definition")

    def test_admin_api_contract_definition_partially_update(self):
        """
        Staff user should be able to partially update a contract_definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definition = factories.ContractDefinitionFactory(
            name=enums.CONTRACT_DEFINITION
        )

        response = self.client.patch(
            f"/api/v1.0/admin/contract-definitions/{contract_definition.id}/",
            content_type="application/json",
            data={"title": "new title"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(contract_definition.id))
        self.assertEqual(content["title"], "new title")

    def test_admin_api_contract_definition_delete(self):
        """
        Staff user should be able to delete a contract definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definition = factories.ContractDefinitionFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/contract-definitions/{contract_definition.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(models.ContractDefinition.objects.exists())

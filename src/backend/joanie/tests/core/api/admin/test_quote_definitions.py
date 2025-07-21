"""Tests for Quote Definition Admin API endpoints."""

from http import HTTPStatus

from django.conf import settings
from django.test import override_settings

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class QuoteDefinitionAdminApiTest(BaseAPITestCase):
    """Test suite for QuoteDefinitionAdminViewSet"""

    def test_api_admin_quote_definition_list_anonymous(self):
        """Anonymous users should not be able to list quote definitions."""
        response = self.client.get("/api/v1.0/admin/quote-definitions/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_quote_definition_list_non_admin(self):
        """Non admin users should not be able to list quote definitions"""
        user = factories.UserFactory()
        self.client.login(username=user.username, password="password")

        response = self.client.get("/api/v1.0/admin/quote-definitions/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_quote_definition_list_admin(self):
        """Admin users should be able to list quote definitions."""
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        factories.QuoteDefinitionFactory.create_batch(2)

        response = self.client.get("/api/v1.0/admin/quote-definitions/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)

    def test_api_admin_quote_definition_list_filter_query_by_title(self):
        """Admin users should be able to filter a quote definition by querying with title"""
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        quote_definition = factories.QuoteDefinitionFactory()

        response = self.client.get(
            f"/api/v1.0/admin/quote-definitions/?query={quote_definition.title}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

        content = response.json()

        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], quote_definition.title)

    @override_settings(LANGUAGES=(("fr-fr", "French"), ("en-us", "English")))
    def test_api_admin_quote_definition_list_filter_query_by_language(self):
        """Admin users should be able to filter a quote definition by querying with language."""
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        for [language, _] in settings.LANGUAGES:
            factories.QuoteDefinitionFactory(language=language)

        for [language, _] in settings.LANGUAGES:
            response = self.client.get(
                f"/api/v1.0/admin/quote-definitions/?language={language}"
            )

            self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

            content = response.json()

            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["language"], language)

    def test_api_admin_quote_definition_list_filter_by_invalid_language(self):
        """Admin users should not be get an error in return if the language filter is invalid."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for [language, _] in settings.LANGUAGES:
            factories.QuoteDefinitionFactory(language=language)

        response = self.client.get(
            "/api/v1.0/admin/quote-definitions/?language=invalid"
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

        content = response.json()

        self.assertEqual(
            content,
            {
                "language": [
                    "Select a valid choice. invalid is not one of the available choices."
                ]
            },
        )

    def test_api_admin_quote_definition_list_filter_by_ids(self):
        """Admin users should be able to get the list of quote definitions by filtering by ids."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        [quote_definition_1, quote_definition_2] = (
            factories.QuoteDefinitionFactory.create_batch(2)
        )

        response = self.client.get(
            f"/api/v1.0/admin/quote-definitions/?ids={quote_definition_1.id}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

        content = response.json()

        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(quote_definition_1.id))

        response = self.client.get(
            f"/api/v1.0/admin/quote-definitions/?ids={quote_definition_1.id}"
            f"&ids={quote_definition_2.id}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

        content = response.json()

        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(quote_definition_1.id))
        self.assertEqual(content["results"][1]["id"], str(quote_definition_2.id))

    def test_api_admin_quote_definition_get(self):
        """Admin users should be able to retrieve a quote definition by its id."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        quote_definition = factories.QuoteDefinitionFactory(
            name=enums.QUOTE_NAME_CHOICES[0][0]
        )

        response = self.client.get(
            f"/api/v1.0/admin/quote-definitions/{quote_definition.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(
            response.json(),
            {
                "id": str(quote_definition.id),
                "title": quote_definition.title,
                "description": quote_definition.description,
                "name": "quote_default",
                "body": quote_definition.body,
                "language": quote_definition.language,
            },
        )

    def test_api_admin_quote_definition_create(self):
        """Admin user should be able to create a quote definition."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        data = {
            "title": "Quote Definition 1",
            "description": "Definition description",
            "body": "Definition body",
            "language": "fr-fr",
            "name": "quote_default",
        }

        response = self.client.post(
            "/api/v1.0/admin/quote-definitions/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        content = response.json()

        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Quote Definition 1")

    def test_api_admin_quote_definition_update(self):
        """Admin users should be able to update a quote definition."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        quote_definition = factories.QuoteDefinitionFactory(
            title="Quote Definition 1",
        )

        data = {
            "title": "Updated Quote Definition 1",
            "language": "fr-fr",
            "name": "quote_default",
        }

        response = self.client.put(
            f"/api/v1.0/admin/quote-definitions/{quote_definition.id}/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

        content = response.json()

        self.assertEqual(content["id"], str(quote_definition.id))
        self.assertEqual(content["title"], "Updated Quote Definition 1")
        self.assertEqual(content["name"], "quote_default")

    def test_api_admin_quote_definition_partially_update(self):
        """Admin users should be able to partially update a quote definition."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        quote_definition = factories.QuoteDefinitionFactory(language="en-us")

        response = self.client.patch(
            f"/api/v1.0/admin/quote-definitions/{quote_definition.id}/",
            content_type="application/json",
            data={"language": "fr-fr"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

        content = response.json()

        self.assertEqual(content["id"], str(quote_definition.id))
        self.assertEqual(content["language"], "fr-fr")

    def test_admin_api_quote_definition_delete(self):
        """
        Admin users should be able to delete a quote definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        quote_definition = factories.QuoteDefinitionFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/quote-definitions/{quote_definition.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(models.QuoteDefinition.objects.exists())

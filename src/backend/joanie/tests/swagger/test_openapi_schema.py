"""
Test suite for generated openapi schema.
"""

import json
from http import HTTPStatus

from django.test import TestCase


class OpenApiSchemaTest(TestCase):
    """
    Test suite for generated openapi schema.
    """

    maxDiff = None

    def test_openapi_client_schema(self):
        """
        Generated OpenAPI client schema should be correct.
        """
        response = self.client.get("/v1.0/swagger.json")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        with open(
            "joanie/tests/swagger/swagger.json", encoding="utf-8"
        ) as expected_schema:
            assert response.json() == json.load(expected_schema)

    def test_openapi_admin_schema(self):
        """
        Generated OpenAPI admin schema should be correct.
        """
        response = self.client.get("/v1.0/admin-swagger.json")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        with open(
            "joanie/tests/swagger/admin-swagger.json", encoding="utf-8"
        ) as expected_schema:
            assert response.json() == json.load(expected_schema)

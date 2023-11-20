"""
Test suite for generated openapi schema.
"""
import json

from django.test import TestCase


class OpenApiSchemaTest(TestCase):
    """
    Test suite for generated openapi schema.
    """

    maxDiff = None

    def test_openapi_schema(self):
        """
        Generated OpenAPI schema should be correct.
        """
        response = self.client.get("/v1.0/swagger.json")

        self.assertEqual(response.status_code, 200)
        with open("joanie/tests/swagger/swagger.json") as expected_schema:
            assert response.json() == json.load(expected_schema)

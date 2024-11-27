"""
Test suite for Product Admin API.
"""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories


class ProductAdminApiCreateTest(TestCase):
    """
    Test suite for the create Product Admin API endpoint.
    """

    maxDiff = None

    def test_admin_api_product_create(self):
        """
        Staff user should be able to create a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "call_to_action": "Purchase now",
            "description": "This is a product description",
            "instructions": "test instruction",
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        self.assertEqual(content["instructions"], "test instruction")

    def test_admin_api_product_create_with_blank_description(self):
        """
        Staff user should be able to create a product with blank description.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "call_to_action": "Purchase now",
            "instructions": "Product instructions",
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        self.assertEqual(content["description"], "")

    def test_admin_api_product_create_with_blank_instructions(self):
        """
        Staff user should be able to create a product with blank instructions.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "description": "This is a product description",
            "call_to_action": "Purchase now",
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        self.assertEqual(content["instructions"], "")

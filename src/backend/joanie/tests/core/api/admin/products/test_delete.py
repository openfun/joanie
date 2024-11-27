"""
Test suite for Product Admin API.
"""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories


class ProductAdminApiDeleteTest(TestCase):
    """
    Test suite for the delete Product Admin API endpoint.
    """

    maxDiff = None

    def test_admin_api_product_delete(self):
        """
        Staff user should be able to delete a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory()

        response = self.client.delete(f"/api/v1.0/admin/products/{product.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

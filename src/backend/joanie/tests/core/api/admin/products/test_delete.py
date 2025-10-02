"""
Test suite for Product Admin API.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class ProductAdminApiDeleteTest(BaseAPITestCase):
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

        self.assertStatusCodeEqual(response, HTTPStatus.NO_CONTENT)

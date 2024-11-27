"""
Test suite for Product Admin API.
"""

import random
from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories, models


class ProductAdminApiListTest(TestCase):
    """
    Test suite for the list Product Admin API endpoint.
    """

    maxDiff = None

    def test_admin_api_product_request_without_authentication(self):
        """
        Anonymous users should not be able to request products endpoint.
        """
        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_product_request_with_lambda_user(self):
        """
        Lambda user should not be able to request products endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_product_list(self):
        """
        Staff user should be able to get paginated list of products
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product_count = random.randint(1, 10)
        factories.ProductFactory.create_batch(product_count)

        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], product_count)

    def test_admin_api_product_list_filter_by_type(self):
        """
        Staff user should be able to get paginated list of products filtered by
        type
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            factories.ProductFactory.create(type=product_type)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            response = self.client.get(f"/api/v1.0/admin/products/?type={product_type}")

            product = models.Product.objects.get(type=product_type)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(product.id))

    def test_admin_api_product_list_filter_by_invalid_type(self):
        """
        Staff user should be able to get paginated list of products filtered by
        type but an error should be returned if the type is not valid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/products/?type=invalid_type")

        self.assertContains(
            response,
            '{"type":["'
            "Select a valid choice. invalid_type is not one of the available choices."
            '"]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_admin_api_product_list_filter_by_id(self):
        """
        Staff user should be able to get paginated list of products filtered by
        id
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        products = factories.ProductFactory.create_batch(3)

        response = self.client.get("/api/v1.0/admin/products/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        response = self.client.get(f"/api/v1.0/admin/products/?ids={products[0].id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(products[0].id))

        response = self.client.get(
            f"/api/v1.0/admin/products/?ids={products[0].id}&ids={products[1].id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(products[1].id))
        self.assertEqual(content["results"][1]["id"], str(products[0].id))

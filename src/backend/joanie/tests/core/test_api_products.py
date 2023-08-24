"""
Test suite for Product Admin API.
"""

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class ProductApiTest(BaseAPITestCase):
    """
    Test suite for Product API.
    """

    def test_api_product_request_without_authentication(self):
        """
        Anonymous users should not be able to request products endpoint.
        """
        response = self.client.get("/api/v1.0/products/")

        self.assertEqual(response.status_code, 401)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_product_list(self):
        """
        Authenticated users should be able to list all products.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.ProductFactory.create_batch(5)
        response = self.client.get(
            "/api/v1.0/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 5)

    def test_api_product_details(self):
        """
        Authenticated users should be able to get a product's details
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(target_courses=[target_course])
        response = self.client.get(
            f"/api/v1.0/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        target_course.refresh_from_db()
        relation = target_course.product_target_relations.first()
        expected_data = {
            "call_to_action": product.call_to_action,
            "certificate_definition": {
                "description": "",
                "name": product.certificate_definition.name,
                "title": product.certificate_definition.title,
            },
            "id": str(product.id),
            "instructions": product.instructions,
            "order_groups": [],
            "price": float(product.price),
            "price_currency": "EUR",
            "state": {
                "priority": product.state["priority"],
                "datetime": product.state["datetime"],
                "call_to_action": product.state["call_to_action"],
                "text": product.state["text"],
            },
            "target_courses": [
                {
                    "code": target_course.code,
                    "course_runs": [],
                    "is_graded": relation.is_graded,
                    "position": relation.position,
                    "title": target_course.title,
                }
            ],
            "title": product.title,
            "type": product.type,
        }
        self.assertEqual(content, expected_data)

    def test_api_product_post(self):
        """
        Users should not be able to create a product.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        product = factories.ProductFactory()
        response = self.client.post(
            f"/api/v1.0/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        content = response.json()
        self.assertEqual(content["detail"], 'Method "POST" not allowed.')

    def test_api_product_patch(self):
        """
        Users should not be able to patch a product.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        product = factories.ProductFactory()
        response = self.client.patch(
            f"/api/v1.0/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        content = response.json()
        self.assertEqual(content["detail"], 'Method "PATCH" not allowed.')

    def test_api_product_put(self):
        """
        Users should not be able to update a product.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        product = factories.ProductFactory()
        response = self.client.put(
            f"/api/v1.0/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        content = response.json()
        self.assertEqual(content["detail"], 'Method "PUT" not allowed.')

    def test_api_product_delete(self):
        """
        Users should not be able to delete a product.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        product = factories.ProductFactory()
        response = self.client.delete(
            f"/api/v1.0/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        content = response.json()
        self.assertEqual(content["detail"], 'Method "DELETE" not allowed.')

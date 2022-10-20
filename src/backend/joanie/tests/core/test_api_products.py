"""Test suite for the Product API"""
from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class ProductApiTest(BaseAPITestCase):
    """Test the API of the Product resource."""

    def test_api_product_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of products for anonymous users.
        """
        factories.ProductFactory()

        response = self.client.get("/api/products/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_product_read_list_authenticated(self):
        """
        It should not be possible to retrieve the list of products for authenticated users.
        """
        factories.ProductFactory()
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/products/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_product_read_detail(self):
        """
        Any users should be allowed to retrieve a product with minimal db access.
        """
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)

        with self.assertNumQueries(2):
            response = self.client.get(f"/api/products/{product.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "call_to_action": product.call_to_action,
                "certificate": {
                    "description": product.certificate_definition.description,
                    "name": product.certificate_definition.name,
                    "title": product.certificate_definition.title,
                },
                "id": str(product.id),
                "price": float(product.price.amount),
                "price_currency": str(product.price.currency),
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organization": {
                            "code": target_course.organization.code,
                            "title": target_course.organization.title,
                        },
                        "course_runs": [
                            {
                                "id": course_run.id,
                                "title": course_run.title,
                                "resource_link": course_run.resource_link,
                                "state": {
                                    "priority": course_run.state["priority"],
                                    "datetime": course_run.state["datetime"]
                                    .isoformat()
                                    .replace("+00:00", "Z"),
                                    "call_to_action": course_run.state[
                                        "call_to_action"
                                    ],
                                    "text": course_run.state["text"],
                                },
                                "start": course_run.start.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "end": course_run.end.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "enrollment_start": course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                                "enrollment_end": course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                            }
                            for course_run in target_course.course_runs.all().order_by(
                                "start"
                            )
                        ],
                        "position": target_course.product_relations.get(
                            product=product
                        ).position,
                        "is_graded": target_course.product_relations.get(
                            product=product
                        ).is_graded,
                        "title": target_course.title,
                    }
                    for target_course in product.target_courses.all().order_by(
                        "product_relations__position"
                    )
                ],
                "title": product.title,
                "type": product.type,
            },
        )

    def test_api_product_read_detail_without_course_anonymous(self):
        """
        An anonymous user should not be allowed to retrieve a product linked to any course.
        """
        product = factories.ProductFactory(courses=[])
        response = self.client.get(f"/api/products/{product.id}/")

        self.assertContains(response, "Not found.", status_code=404)

    def test_api_product_read_detail_without_course_authenticated(self):
        """
        An authenticated user should not be allowed to retrieve a product linked to any course.
        """
        product = factories.ProductFactory(courses=[])
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/products/{product.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(response, "Not found.", status_code=404)

    def test_api_product_create_anonymous(self):
        """Anonymous users should not be allowed to create a product."""
        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.post("/api/products/", data=data)

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.Product.objects.count(), 0)

    def test_api_product_create_authenticated(self):
        """Authenticated users should not be allowed to create a product."""
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.post(
            "/api/products/", data=data, HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.Product.objects.count(), 0)

    def test_api_product_update_anonymous(self):
        """Anonymous users should not be allowed to update a product."""
        product = factories.ProductFactory(price=100.0)

        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.put(f"/api/products/{product.id}/", data=data)

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_update_authenticated(self):
        """Authenticated users should not be allowed to update a product."""
        product = factories.ProductFactory(price=100.0)
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.put(
            f"/api/products/{product.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_partial_update_anonymous(self):
        """Anonymous users should not be allowed to partially update a product."""
        product = factories.ProductFactory(price=100.0)

        data = {"price": 1337.00}

        response = self.client.patch(f"/api/products/{product.id}/", data=data)

        self.assertContains(
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_partial_update_authenticated(self):
        """Authenticated users should not be allowed to partially update a product."""
        product = factories.ProductFactory(price=100.0)
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        data = {
            "price": 1337.00,
        }

        response = self.client.patch(
            f"/api/products/{product.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_delete_anonymous(self):
        """Anonymous users should not be allowed to delete a product."""
        product = factories.ProductFactory()

        response = self.client.delete(f"/api/products/{product.id}/")

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )
        self.assertEqual(models.Product.objects.count(), 1)

    def test_api_product_delete_authenticated(self):
        """Authenticated users should not be allowed to delete a product."""
        product = factories.ProductFactory()
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/products/{product.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )
        self.assertEqual(models.Product.objects.count(), 1)

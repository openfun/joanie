"""
Test suite for Product Admin API.
"""
import random

from django.test import TestCase

from joanie.core import factories, models


class ProductAdminApiTest(TestCase):
    """
    Test suite for Product Admin API.
    """

    def test_admin_api_product_request_without_authentication(self):
        """
        Anonymous users should not be able to request products endpoint.
        """
        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, 403)
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

        self.assertEqual(response.status_code, 403)
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

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], product_count)

    def test_admin_api_product_get(self):
        """
        Staff user should be able to get a product through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory()

        response = self.client.get(f"/api/v1.0/admin/products/{product.id}/")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))

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
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, 201)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")

    def test_admin_api_product_create_nested(self):
        """
        Staff user should be able to create a product with nested elements.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        course = factories.CourseFactory()
        data = {
            "title": "Product 001",
            "description": "This is a product description",
            "call_to_action": "Purchase now",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "target_courses": [
                {
                    "title": "TargetCourse00",
                    "code": "TARGETCOURSECODE00",
                    "organizations": [str(organization.id)],
                },
            ],
            "course_relations": [
                {
                    "organizations": [str(organization.id)],
                    "course": str(course.id),
                },
            ],
        }

        response = self.client.post(
            "/api/v1.0/admin/products/",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        self.assertTrue(
            models.Course.objects.filter(code="TARGETCOURSECODE00").exists()
        )
        self.assertTrue(
            models.CourseProductRelation.objects.filter(
                course__id=course.id, organizations=organization.id
            ).exists()
        )

    def test_admin_api_product_create_edit_nested(self):
        """
        Staff user should be able to create a product with nested elements.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        course = factories.CourseFactory()
        data = {
            "title": "Product 001",
            "description": "This is a product description",
            "call_to_action": "Purchase now",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "target_courses": [
                {
                    "title": "TargetCourse00",
                    "code": "TARGETCOURSECODE00",
                    "organizations": [str(organization.id)],
                },
            ],
            "course_relations": [
                {
                    "organizations": [str(organization.id)],
                    "course": str(course.id),
                },
            ],
        }

        response = self.client.post(
            "/api/v1.0/admin/products/",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        target_course = models.Course.objects.get(code="TARGETCOURSECODE00")
        data = {
            "title": "Product 001",
            "description": "This is a product description",
            "call_to_action": "Purchase now",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "target_courses": [
                {
                    "id": str(target_course.id),
                    "title": "TargetCourse00",
                    "code": "TARGETCOURSECODE01",
                    "organizations": [str(organization.id)],
                },
            ],
            "course_relations": [
                {
                    "organizations": [str(organization.id)],
                    "course": str(course.id),
                },
            ],
        }
        response = self.client.post(
            "/api/v1.0/admin/products/",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        target_course.refresh_from_db()
        self.assertEqual(target_course.code, "TARGETCOURSECODE01")

    def test_admin_api_product_update(self):
        """
        Staff user should be able to update a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(price=200)
        payload = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "call_to_action": "Purchase now",
            "description": "This is a product description",
        }

        response = self.client.put(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        self.assertEqual(content["price"], 100)

    def test_admin_api_product_partially_update(self):
        """
        Staff user should be able to partially update a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(price=100)

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"price": 100.57, "price_currency": "EUR"},
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        self.assertEqual(content["price"], 100.57)

    def test_admin_api_product_delete(self):
        """
        Staff user should be able to delete a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory()

        response = self.client.delete(f"/api/v1.0/admin/products/{product.id}/")

        self.assertEqual(response.status_code, 204)

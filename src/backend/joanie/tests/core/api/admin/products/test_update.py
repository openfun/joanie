"""
Test suite for Product Admin API.
"""

import random
from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class ProductAdminApiUpdateTest(BaseAPITestCase):
    """
    Test suite for the update Product Admin API endpoint.
    """

    maxDiff = None

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
            "type": random.choice(["credential", "certificate"]),
            "call_to_action": "Purchase now",
            "description": "This is a product description",
            "instructions": "This is a test instruction",
        }

        response = self.client.put(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        self.assertEqual(content["price"], 100)
        self.assertEqual(content["instructions"], "This is a test instruction")

    def test_admin_api_product_update_partially(self):
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

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        self.assertEqual(content["price"], 100.57)

    def test_admin_api_product_update_certification(self):
        """
        Staff user should be able to update certification level field.
        This field should be None or a positive integer between 1 and 9.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"certification_level": "one"},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "certification_level": [
                    "Certification level must be an integer or null."
                ]
            },
        )

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"certification_level": 0},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "certification_level": [
                    "Ensure this value is greater than or equal to 1."
                ]
            },
        )

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"certification_level": 9},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"certification_level": ["Ensure this value is less than or equal to 8."]},
        )

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"certification_level": 2},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        product.refresh_from_db()
        self.assertEqual(product.certification_level, 2)

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"certification_level": None},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        product.refresh_from_db()
        self.assertEqual(product.certification_level, None)

    def test_admin_api_product_update_teachers(self):
        """
        Staff user should be able to update teachers of a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        teacher = factories.TeacherFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"teachers": [str(teacher.id)]},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        product.refresh_from_db()
        self.assertEqual(product.teachers.count(), 1)
        self.assertEqual(product.teachers.first().id, teacher.id)

        # Then unset teachers
        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"teachers": []},
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        product.refresh_from_db()
        self.assertEqual(product.teachers.count(), 0)

    def test_admin_api_product_update_skills(self):
        """
        Staff user should be able to update skills of a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        skill = factories.SkillFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"skills": [str(skill.id)]},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        product.refresh_from_db()
        self.assertEqual(product.skills.count(), 1)
        self.assertEqual(product.skills.first().id, skill.id)

    def test_admin_api_product_update_empty_instructions(self):
        """
        Staff user should be able to update a product with empty instructions.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(
            price=100, instructions="A not empty instruction"
        )

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"instructions": ""},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["instructions"], "")
        product.refresh_from_db()
        self.assertEqual(product.instructions, "")

    def test_admin_api_product_update_trailing_whitespace(self):
        """
        Trailing whitespaces and newline on instructions should remain
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(price=100)

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"instructions": "Test whitespace   "},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["instructions"], "Test whitespace   ")

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"instructions": "Test newline\n\n"},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["instructions"], "Test newline\n\n")

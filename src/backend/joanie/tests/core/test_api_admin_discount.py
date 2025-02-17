"""
Test suite for Discount Admin API.
"""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories


class DiscountAdminApiTest(TestCase):
    """
    Test suite for Discount Admin API.
    """

    def test_api_admin_discount_anonymous_get_list(self):
        """Anonymous user should not be able to get the list of discounts"""
        response = self.client.get("/api/v1.0/admin/discounts/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_admin_authenticated_discount_get_list(self):
        """Authenticated admin user should be able to get the list of discounts"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        discounts = factories.DiscountFactory.create_batch(2)
        factories.OrderGroupFactory.create_batch(2, discount=discounts[0])

        response = self.client.get("/api/v1.0/admin/discounts/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "id": str(discounts[0].id),
                    "amount": discounts[0].amount,
                    "rate": discounts[0].rate,
                    "is_used": 2,
                },
                {
                    "id": str(discounts[1].id),
                    "amount": discounts[1].amount,
                    "rate": discounts[1].rate,
                    "is_used": 0,
                },
            ],
        )

    def test_api_admin_authenticated_discount_delete(self):
        """Authenticated admin user should not be able to delete a discount"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        discount = factories.DiscountFactory()

        response = self.client.delete(f"/api/v1.0/admin/discounts/{discount.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_api_admin_authenticated_discount_partially_update(self):
        """Authenticated admin user should not be able to partially update a discount"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        discount = factories.DiscountFactory(rate=0.3, amount=None)

        response = self.client.patch(
            f"/api/v1.0/admin/discounts/{discount.id}/",
            content_type="application/json",
            data={
                "rate": 0.1,
            },
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(content["rate"], 0.1)

    def test_api_admin_authenticated_discount_update(self):
        """Authenticated admin user should not be able to update a discount"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        discount = factories.DiscountFactory(rate=0.3)

        response = self.client.put(
            f"/api/v1.0/admin/discounts/{discount.id}/",
            content_type="application/json",
            data={
                "rate": None,
                "amount": 33,
            },
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(content["amount"], 33)
        self.assertIsNone(content["rate"])

    def test_api_admin_authenticated_discount_create(self):
        """Authenticated admin user should be able to create a discount"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/discounts/",
            content_type="application/json",
            data={"rate": 0.2, "amount": None},
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(content["rate"], 0.2)
        self.assertIsNone(content["amount"])

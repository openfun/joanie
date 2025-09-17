# pylint: disable=too-many-instance-attributes
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
        factories.OfferingRuleFactory.create_batch(2, discount=discounts[0])

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


class DiscountAdminApiListFilterTest(TestCase):
    """
    Test suite for Discount Admin API list filter.
    """

    maxDiff = None

    def setUp(self):
        """
        Set up the test case.
        """

        self.amount_10 = factories.DiscountFactory(amount=10)
        self.amount_100 = factories.DiscountFactory(amount=100)
        self.amount_101 = factories.DiscountFactory(amount=101)
        self.rate_10 = factories.DiscountFactory(rate=0.1)
        self.rate_11 = factories.DiscountFactory(rate=0.11)
        self.amount_20 = factories.DiscountFactory(amount=20)
        self.amount_200 = factories.DiscountFactory(amount=200)
        self.amount_201 = factories.DiscountFactory(amount=201)
        self.rate_20 = factories.DiscountFactory(rate=0.2)
        self.rate_21 = factories.DiscountFactory(rate=0.21)
        self.discounts = [
            self.amount_10,
            self.amount_100,
            self.amount_101,
            self.rate_10,
            self.rate_11,
            self.amount_20,
            self.amount_200,
            self.amount_201,
            self.rate_20,
            self.rate_21,
        ]

    def _test_discounts_results(self, response, expected_discounts):
        """
        Helper method to test the response of the API.
        """
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "count": len(expected_discounts),
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(discount.id),
                        "amount": discount.amount,
                        "rate": discount.rate,
                        "is_used": 0,
                    }
                    for discount in expected_discounts
                ],
            },
        )

    def test_api_admin_discount_list_filtered_by_numbers(self):
        """
        Authenticated admin user should be able to get the list of discounts
        filtered by number.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/discounts/?query=10")

        self._test_discounts_results(
            response,
            [
                self.amount_10,
                self.amount_100,
                self.amount_101,
                self.rate_10,
                self.rate_11,
            ],
        )

    def test_api_admin_discount_list_filtered_by_number(self):
        """
        Authenticated admin user should be able to get the list of discounts
        filtered by number.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/discounts/?query=1")

        self._test_discounts_results(
            response,
            [
                self.amount_10,
                self.amount_100,
                self.amount_101,
                self.rate_10,
                self.rate_11,
                self.amount_201,
                self.rate_21,
            ],
        )

    def test_api_admin_discount_list_filtered_by_type_amount(self):
        """
        Authenticated admin user should be able to get the list of discounts
        filtered by type (€).
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/discounts/?query=€")

        self._test_discounts_results(
            response,
            [
                self.amount_10,
                self.amount_100,
                self.amount_101,
                self.amount_20,
                self.amount_200,
                self.amount_201,
            ],
        )

    def test_api_admin_discount_list_filtered_by_type_rate(self):
        """
        Authenticated admin user should be able to get the list of discounts
        filtered by type (%).
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/discounts/?query=%")

        self._test_discounts_results(
            response,
            [
                self.rate_10,
                self.rate_11,
                self.rate_20,
                self.rate_21,
            ],
        )

    def test_api_admin_discount_list_filtered_by_specific_rate(self):
        """
        Authenticated admin user should be able to get the list of discounts
        filtered by type (%).
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/discounts/?query=21")

        self._test_discounts_results(
            response,
            [
                self.rate_21,
            ],
        )

    def test_api_admin_discount_list_filtered_by_type_and_number(self):
        """
        Authenticated admin user should be able to get the list of discounts
        filtered by type and number.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/discounts/?query=20€")

        self._test_discounts_results(response, [self.amount_20])

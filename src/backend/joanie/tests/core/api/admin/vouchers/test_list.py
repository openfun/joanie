"""Test suite for the admin vouchers API list endpoint."""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class VouchersAdminApiListTestCase(BaseAPITestCase):
    """Test suite for the admin vouchers API list endpoint."""

    maxDiff = None

    def test_api_admin_vouchers_list_without_authentication(self):
        """
        Anonymous users should not be able to request vouchers endpoint.
        """
        response = self.client.get("/api/v1.0/admin/vouchers/")

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_vouchers_list_with_lambda_user(self):
        """
        Lambda user should not be able to request vouchers endpoint.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.get("/api/v1.0/admin/vouchers/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_vouchers_list_with_staff_user(self):
        """
        Staff user should be able to list all existing vouchers.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        voucher = factories.VoucherFactory()

        response = self.client.get("/api/v1.0/admin/vouchers/")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(voucher.id),
                        "code": voucher.code,
                        "discount": {
                            "id": str(voucher.discount.id),
                            "is_used": voucher.discount.usage_count,
                            "amount": voucher.discount.amount,
                            "rate": voucher.discount.rate,
                        },
                        "is_active": True,
                        "multiple_use": False,
                        "multiple_users": False,
                        "created_on": format_date(voucher.created_on),
                        "updated_on": format_date(voucher.updated_on),
                        "orders_count": voucher.orders.count(),
                    }
                ],
            },
            response.json(),
        )

    def test_api_admin_vouchers_list(self):
        """Authenticated admin user should be able to list all existing vouchers."""
        # Create some vouchers
        vouchers = factories.VoucherFactory.create_batch(3)

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/vouchers/")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        content = response.json()
        expected_content = {
            "count": 3,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": str(voucher.id),
                    "code": voucher.code,
                    "discount": {
                        "id": str(voucher.discount.id),
                        "is_used": voucher.discount.usage_count,
                        "amount": voucher.discount.amount,
                        "rate": voucher.discount.rate,
                    },
                    "is_active": True,
                    "multiple_use": False,
                    "multiple_users": False,
                    "created_on": format_date(voucher.created_on),
                    "updated_on": format_date(voucher.updated_on),
                    "orders_count": voucher.orders.count(),
                }
                for voucher in vouchers
            ],
        }

        self.assertEqual(expected_content, content)

    def test_api_admin_vouchers_list_pagination(self):
        """Pagination should work as expected."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        factories.VoucherFactory.create_batch(5)

        response = self.client.get("/api/v1.0/admin/vouchers/?page_size=2")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(5, content["count"])
        self.assertEqual(
            "http://testserver/api/v1.0/admin/vouchers/?page=2&page_size=2",
            content["next"],
        )
        self.assertIsNone(content["previous"])
        self.assertEqual(2, len(content["results"]))

        response = self.client.get("/api/v1.0/admin/vouchers/?page_size=2&page=2")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(5, content["count"])
        self.assertEqual(
            "http://testserver/api/v1.0/admin/vouchers/?page=3&page_size=2",
            content["next"],
        )
        self.assertEqual(
            "http://testserver/api/v1.0/admin/vouchers/?page_size=2",
            content["previous"],
        )
        self.assertEqual(2, len(content["results"]))

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

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_admin_vouchers_list_with_lambda_user(self):
        """
        Lambda user should not be able to request vouchers endpoint.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.get("/api/v1.0/admin/vouchers/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_api_admin_vouchers_list(self):
        """Authenticated admin user should be able to list all existing vouchers."""
        # Create some vouchers
        vouchers = factories.VoucherFactory.create_batch(3)

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/vouchers/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        expected_content = {
            "count": 3,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": str(voucher.id),
                    "code": voucher.code,
                    "discount_id": str(voucher.discount.id)
                    if voucher.discount
                    else None,
                    "order_group_id": str(voucher.order_group.id)
                    if voucher.order_group
                    else None,
                    "multiple_use": False,
                    "multiple_users": False,
                    "created_on": format_date(voucher.created_on),
                    "updated_on": format_date(voucher.updated_on),
                }
                for voucher in vouchers
            ],
        }

        self.assertEqual(content, expected_content)

    def test_api_admin_vouchers_list_pagination(self):
        """Pagination should work as expected."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        factories.VoucherFactory.create_batch(5)

        response = self.client.get("/api/v1.0/admin/vouchers/?page_size=2")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 5)
        self.assertEqual(
            content["next"],
            "http://testserver/api/v1.0/admin/vouchers/?page=2&page_size=2",
        )
        self.assertIsNone(content["previous"])
        self.assertEqual(len(content["results"]), 2)

        response = self.client.get("/api/v1.0/admin/vouchers/?page_size=2&page=2")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 5)
        self.assertEqual(
            content["next"],
            "http://testserver/api/v1.0/admin/vouchers/?page=3&page_size=2",
        )
        self.assertEqual(
            content["previous"],
            "http://testserver/api/v1.0/admin/vouchers/?page_size=2",
        )
        self.assertEqual(len(content["results"]), 2)

"""Test suite for the admin vouchers API create endpoint."""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class VouchersAdminApiCreateTestCase(BaseAPITestCase):
    """Test suite for the admin vouchers API create endpoint."""

    maxDiff = None

    def test_api_admin_vouchers_create_anonymous(self):
        """Anonymous users should not be able to create a voucher."""
        response = self.client.post("/api/v1.0/admin/vouchers/")

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_admin_vouchers_create_authenticated_with_lambda_user(self):
        """Lambda users should not be able to create a voucher."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.post("/api/v1.0/admin/vouchers/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_api_admin_vouchers_create(self):
        """Admin users should be able to create a voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        discount = factories.DiscountFactory()

        data = {
            "code": "TEST_VOUCHER",
            "discount_id": str(discount.id),
            "multiple_use": False,
            "multiple_users": False,
        }

        response = self.client.post("/api/v1.0/admin/vouchers/", data)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        self.assertEqual(models.Voucher.objects.count(), 1)
        voucher = models.Voucher.objects.first()
        self.assertEqual(voucher.code, "TEST_VOUCHER")
        self.assertEqual(voucher.discount, discount)
        self.assertEqual(voucher.multiple_use, False)
        self.assertEqual(voucher.multiple_users, False)
        self.assertEqual(
            response.json(),
            {
                "id": str(voucher.id),
                "code": "TEST_VOUCHER",
                "discount_id": str(discount.id),
                "order_group_id": None,
                "multiple_use": False,
                "multiple_users": False,
                "created_on": format_date(voucher.created_on),
                "updated_on": format_date(voucher.updated_on),
            },
        )

    def test_api_admin_vouchers_create_with_invalid_data(self):
        """Admin users should not be able to create a voucher with invalid data."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        data = {}

        response = self.client.post("/api/v1.0/admin/vouchers/", data)

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"__all__": ["Voucher discount or order group is required."]},
        )

    def test_api_admin_vouchers_create_with_duplicate_code(self):
        """Admin users should not be able to create a voucher with a duplicate code."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        factories.VoucherFactory(code="DUPLICATE_CODE")
        discount = factories.DiscountFactory()

        # Try to create another voucher with the same code
        data = {
            "code": "DUPLICATE_CODE",
            "discount_id": str(discount.id),
        }

        response = self.client.post("/api/v1.0/admin/vouchers/", data)

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        content = response.json()
        self.assertIn("code", content)

"""Test suite for the admin vouchers API retrieve endpoint."""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class VouchersAdminApiRetrieveTestCase(BaseAPITestCase):
    """Test suite for the admin vouchers API retrieve endpoint."""

    maxDiff = None

    def test_api_admin_vouchers_retrieve_anonymous(self):
        """Anonymous users should not be able to retrieve a voucher."""
        voucher = factories.VoucherFactory()
        response = self.client.get(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_admin_vouchers_retrieve_authenticated_with_lambda_user(self):
        """Lambda users should not be able to retrieve a voucher."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        voucher = factories.VoucherFactory()
        response = self.client.get(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_api_admin_vouchers_retrieve(self):
        """Admin users should be able to retrieve a voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher = factories.VoucherFactory()

        response = self.client.get(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        expected_content = {
            "id": str(voucher.id),
            "created_on": format_date(voucher.created_on),
            "updated_on": format_date(voucher.updated_on),
            "code": voucher.code,
            "order_group_id": str(voucher.order_group.id),
            "discount_id": None,
            "multiple_use": voucher.multiple_use,
            "multiple_users": voucher.multiple_users,
        }

        self.assertEqual(content, expected_content)

    def test_api_admin_vouchers_retrieve_with_discount(self):
        """Admin users should be able to retrieve a voucher with a discount."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher = factories.VoucherFactory(
            order_group=None,
            discount=factories.DiscountFactory(rate=0.3, amount=None),
        )

        response = self.client.get(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        expected_content = {
            "id": str(voucher.id),
            "created_on": format_date(voucher.created_on),
            "updated_on": format_date(voucher.updated_on),
            "code": voucher.code,
            "order_group_id": None,
            "discount_id": str(voucher.discount.id),
            "multiple_use": voucher.multiple_use,
            "multiple_users": voucher.multiple_users,
        }

        self.assertEqual(content, expected_content)

    def test_api_admin_vouchers_retrieve_non_existing(self):
        """Admin users should receive a 404 when trying to retrieve a non-existing voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/vouchers/non-existing-id/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

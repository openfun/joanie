"""Test suite for the admin vouchers API update endpoint."""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class VouchersAdminApiUpdateTestCase(BaseAPITestCase):
    """Test suite for the admin vouchers API update endpoint."""

    maxDiff = None

    def test_api_admin_vouchers_update_anonymous(self):
        """Anonymous users should not be able to update a voucher."""
        voucher = factories.VoucherFactory()
        response = self.client.put(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_admin_vouchers_update_authenticated_with_lambda_user(self):
        """Lambda users should not be able to update a voucher."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        voucher = factories.VoucherFactory()
        response = self.client.put(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_api_admin_vouchers_update(self):
        """Admin users should be able to update a voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher = factories.VoucherFactory(
            code="OLD_CODE",
            multiple_use=True,
            multiple_users=True,
        )

        data = {
            "code": "NEW_CODE",
            "multiple_use": False,
            "multiple_users": False,
        }

        response = self.client.put(
            f"/api/v1.0/admin/vouchers/{voucher.id}/",
            data=data,
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        voucher.refresh_from_db()
        self.assertEqual(voucher.code, "NEW_CODE")
        self.assertFalse(voucher.multiple_use)
        self.assertFalse(voucher.multiple_users)

        self.assertEqual(
            response.json(),
            {
                "id": str(voucher.id),
                "code": "NEW_CODE",
                "discount_id": str(voucher.discount.id) if voucher.discount else None,
                "order_group_id": str(voucher.order_group.id)
                if voucher.order_group
                else None,
                "multiple_use": False,
                "multiple_users": False,
                "created_on": format_date(voucher.created_on),
                "updated_on": format_date(voucher.updated_on),
            },
        )

    def test_api_admin_vouchers_partial_update(self):
        """Admin users should be able to partially update a voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create a voucher
        voucher = factories.VoucherFactory(code="OLD_CODE")

        # Update only some fields
        data = {"code": "NEW_CODE"}

        response = self.client.patch(
            f"/api/v1.0/admin/vouchers/{voucher.id}/",
            content_type="application/json",
            data=data,
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        # Check that the voucher is updated in the database
        voucher.refresh_from_db()
        self.assertEqual(voucher.code, "NEW_CODE")

    def test_api_admin_vouchers_update_with_invalid_data(self):
        """Admin users should not be able to update a voucher with invalid data."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher = factories.VoucherFactory()

        data = {"code": ""}

        response = self.client.put(
            f"/api/v1.0/admin/vouchers/{voucher.id}/",
            data=data,
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        content = response.json()
        self.assertIn("code", content)

    def test_api_admin_vouchers_update_with_duplicate_code(self):
        """Admin users should not be able to update a voucher with a duplicate code."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher1 = factories.VoucherFactory()
        voucher2 = factories.VoucherFactory()

        data = {"code": voucher1.code}

        response = self.client.put(
            f"/api/v1.0/admin/vouchers/{voucher2.id}/",
            data=data,
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"code": ["Voucher with this code already exists."]},
        )

    def test_api_admin_vouchers_update_non_existing(self):
        """Admin users should receive a 404 when trying to update a non-existing voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.put(
            "/api/v1.0/admin/vouchers/non-existing-id/",
            data={},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

"""Test suite for the admin vouchers API delete endpoint."""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class VouchersAdminApiDeleteTestCase(BaseAPITestCase):
    """Test suite for the admin vouchers API delete endpoint."""

    maxDiff = None

    def test_api_admin_vouchers_delete_anonymous(self):
        """Anonymous users should not be able to delete a voucher."""
        voucher = factories.VoucherFactory()
        response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_admin_vouchers_delete_authenticated_with_lambda_user(self):
        """Lambda users should not be able to delete a voucher."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        voucher = factories.VoucherFactory()
        response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_api_admin_vouchers_delete(self):
        """Admin users should be able to delete a voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher = factories.VoucherFactory()
        response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        # Check that the voucher is deleted from the database
        self.assertEqual(models.Voucher.objects.count(), 0)

    def test_api_admin_vouchers_delete_non_existing(self):
        """Admin users should receive a 404 when trying to delete a non-existing voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.delete("/api/v1.0/admin/vouchers/non-existing-id/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # def test_api_admin_vouchers_delete_with_orders(self):
    #     """Admin users should be able to delete a voucher even if it has been used in orders."""
    #     admin = factories.UserFactory(is_staff=True, is_superuser=True)
    #     self.client.login(username=admin.username, password="password")
    #
    #     # Create a voucher
    #     voucher = factories.VoucherFactory()
    #
    #     # Create an order that uses the voucher
    #     order = factories.OrderFactory(product=voucher.product)
    #     order.voucher = voucher
    #     order.save()
    #
    #     # Delete the voucher
    #     response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")
    #
    #     self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
    #
    #     # Check that the voucher is deleted from the database
    #     self.assertEqual(models.Voucher.objects.count(), 0)
    #
    #     # Check that the order still exists but no longer references the voucher
    #     order.refresh_from_db()
    #     self.assertIsNone(order.voucher)

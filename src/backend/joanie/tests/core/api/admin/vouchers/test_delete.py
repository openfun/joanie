"""Test suite for the admin vouchers API delete endpoint."""

from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class VouchersAdminApiDeleteTestCase(BaseAPITestCase):
    """Test suite for the admin vouchers API delete endpoint."""

    maxDiff = None

    def test_api_admin_vouchers_delete_anonymous(self):
        """Anonymous users should not be able to delete a voucher."""
        voucher = factories.VoucherFactory()
        response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_vouchers_delete_authenticated_with_lambda_user(self):
        """Lambda users should not be able to delete a voucher."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        voucher = factories.VoucherFactory()

        response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_vouchers_delete_authenticated_with_staff_user(self):
        """Staff users should not be able to delete a voucher."""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        voucher = factories.VoucherFactory()

        response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

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

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_admin_vouchers_delete_with_orders(self):
        """
        Admin users should be able to delete a voucher even if it has been used in orders.
        The order's total should not change since it has been freeze when initialized.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher = factories.VoucherFactory(
            discount=factories.DiscountFactory(rate=0.1),
            multiple_use=False,
        )
        offering = factories.OfferingFactory(product__price=100)
        order = factories.OrderGeneratorFactory(
            voucher=voucher,
            course=offering.course,
            organization=offering.organizations.first(),
            product=offering.product,
            state=enums.ORDER_STATE_COMPLETED,
        )

        response = self.client.delete(f"/api/v1.0/admin/vouchers/{voucher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        # Check that the voucher is deleted from the database
        self.assertEqual(models.Voucher.objects.count(), 0)

        # Check that the order still exists but no longer references the voucher
        order.refresh_from_db()
        self.assertIsNone(order.voucher)
        self.assertEqual(order.total, 90)

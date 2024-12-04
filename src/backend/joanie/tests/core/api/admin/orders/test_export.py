"""Test suite for the admin orders API export endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories
from joanie.tests import format_date


class OrdersAdminApiExportTestCase(TestCase):
    """Test suite for the admin orders API export endpoint."""

    maxDiff = None

    def test_api_admin_orders_export_csv_anonymous_user(self):
        """
        Anonymous users should not be able to export orders as CSV.
        """
        response = self.client.get("/api/v1.0/admin/orders/export/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_orders_export_csv_lambda_user(self):
        """
        Lambda users should not be able to export orders as CSV.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/export/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_export_csv(self):
        """
        Admin users should be able to export orders as CSV.
        """
        orders = factories.OrderFactory.create_batch(3)
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/export/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="orders.csv"',
        )
        csv_content = response.content.decode().splitlines()
        csv_header = csv_content.pop(0)
        self.assertEqual(
            csv_header.split(","),
            [
                "id",
                "created_on",
                "owner",
                "total",
            ],
        )

        for order, csv_line in zip(orders, csv_content, strict=False):
            csv_row = csv_line.split(",")
            self.assertEqual(csv_row[0], str(order.id))
            self.assertEqual(csv_row[1], format_date(order.created_on))
            self.assertEqual(csv_row[2], order.owner.username)
            self.assertEqual(csv_row[3], str(order.total))

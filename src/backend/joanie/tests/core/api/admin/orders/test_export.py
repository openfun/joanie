"""Test suite for the admin orders API export endpoint."""

from http import HTTPStatus
from unittest import mock

from django.test import TestCase
from django.utils import timezone

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
        orders = factories.OrderGeneratorFactory.create_batch(3)
        orders.reverse()
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get("/api/v1.0/admin/orders/export/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="orders_{now.strftime("%d-%m-%Y_%H-%M-%S")}.csv"',
        )
        csv_content = response.getvalue().decode().splitlines()
        csv_header = csv_content.pop(0)
        self.assertEqual(
            csv_header.split(","),
            [
                "Référence de commande",
                "Date de création",
                "Propriétaire",
                "Prix",
            ],
        )

        for order, csv_line in zip(orders, csv_content, strict=False):
            self.assertEqual(
                csv_line.split(","),
                [
                    str(order.id),
                    format_date(order.created_on),
                    order.owner.get_full_name(),
                    str(order.total),
                ],
            )

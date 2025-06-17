"""Test suite for the admin batch orders API read list endpoint."""

from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories


class BatchOrdersAdminApiListTestCase(TestCase):
    """Test suite for the admin batch orders API read list endpoint."""

    def test_api_admin_read_list_batch_orders_anonymous(self):
        """Anonymous user should not be able to list the batch orders"""
        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_read_list_batch_orders_authenticated_user(self):
        """Authenticated user should not be able to list batch orders"""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_read_list_batch_orders_list_authenticated_admin(self):
        """Authenticated admin user should be able to list batch orders"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_orders = factories.BatchOrderFactory.create_batch(
            3, state=enums.BATCH_ORDER_STATE_ASSIGNED
        )

        expected_return = [
            {
                "id": str(batch_order.id),
                "address": batch_order.address,
                "city": batch_order.city,
                "company_name": batch_order.company_name,
                "contract_id": str(batch_order.contract.id),
                "country": batch_order.country.code,
                "currency": settings.DEFAULT_CURRENCY,
                "identification_number": batch_order.identification_number,
                "main_invoice_reference": str(batch_order.main_invoice.reference),
                "nb_seats": batch_order.nb_seats,
                "organization": {
                    "code": batch_order.organization.code,
                    "id": str(batch_order.organization.id),
                    "title": batch_order.organization.title,
                },
                "owner": str(batch_order.owner.id),
                "postcode": batch_order.postcode,
                "offer": str(batch_order.offer.id),
                "total": float(batch_order.total),
                "trainees": batch_order.trainees,
                "voucher": None,
                "vouchers": [],
                "offer_rules": [],
            }
            for batch_order in batch_orders
        ]

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json()["results"], expected_return)

"""Test suite for the admin batch orders API read detail endpoint."""

from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories


class BatchOrdersAdminApiDetailTestCase(TestCase):
    """Test suite for the admin batch orders API read detail endpoint."""

    def test_api_admin_read_detail_batch_order_anonymous(self):
        """Anonymous user should not be able to read detail of a batch order"""
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_read_detail_batch_order_authenticated(self):
        """Authenticated user should not be able to read the detail of a batch order"""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_read_detail_batch_order_admin_authenticated(self):
        """Authenticated admin user should be able to read the detail of a batch order"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED
        )

        response = self.client.get(f"/api/v1.0/admin/batch-orders/{batch_order.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertDictEqual(
            response.json(),
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
                "offering": str(batch_order.offering.id),
                "total": float(batch_order.total),
                "trainees": batch_order.trainees,
                "vouchers": [],
                "offering_rules": [],
                "voucher": None,
            },
        )

"""Test suite for the admin batch orders API list endpoint."""

from http import HTTPStatus

from django.conf import settings

from joanie.core import enums, factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class BatchOrdersAdminApiListTestCase(BaseAPITestCase):
    """Test suite for the admin batch orders API list endpoint."""

    def test_api_admin_batch_orders_list_anonymous(self):
        """Anonymous user should not be able to list the batch orders"""
        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_orders_list_authenticated_user(self):
        """Authenticated user should not be able to list batch orders"""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_orders_list_authenticated_admin(self):
        """Authenticated admin user should be able to list batch orders"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_orders = factories.BatchOrderFactory.create_batch(
            3,
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(
            [
                {
                    "id": str(batch_order.id),
                    "company_name": batch_order.company_name,
                    "owner_name": batch_order.owner.name,
                    "organization_title": batch_order.organization.title,
                    "product_title": batch_order.offering.product.title,
                    "course_code": batch_order.offering.course.code,
                    "nb_seats": batch_order.nb_seats,
                    "state": batch_order.state,
                    "created_on": format_date(batch_order.created_on),
                    "updated_on": format_date(batch_order.updated_on),
                    "total": float(batch_order.total),
                    "total_currency": settings.DEFAULT_CURRENCY,
                    "payment_method": batch_order.payment_method,
                }
                for batch_order in batch_orders
            ],
            response.json()["results"],
        )

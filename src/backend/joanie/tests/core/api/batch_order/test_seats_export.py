"""Test suite for BatchOrder seats CSV export API endpoint."""

from http import HTTPStatus

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class BatchOrderSeatsExportAPITest(BaseAPITestCase):
    """Tests for BatchOrder seats CSV export endpoint."""

    maxDiff = None

    def test_api_batch_order_seats_export_anonymous(self):
        """Anonymous users should not be able to export seats."""
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats-export/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_batch_order_seats_export_not_owner(self):
        """
        Authenticated users should not be able to export seats
        of a batch order they do not own.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats-export/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_batch_order_seats_export_no_orders(self):
        """
        When a batch order has no generated orders yet,
        the CSV should contain only the header row.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_SIGNING,
        )

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats-export/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="batch_order_{batch_order.id}_seats.csv"',
        )

        csv_content = response.getvalue().decode().strip().splitlines()
        self.assertEqual(len(csv_content), 1)
        self.assertEqual(
            csv_content[0],
            "Last name,First name,Email",
        )

    def test_api_batch_order_seats_export_with_orders(self):
        """
        When a batch order has generated orders, the CSV should list
        the seats (order owners) with their name and email.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
        )

        # Create individual orders linked to this batch order
        learner_1 = factories.UserFactory(
            first_name="Alice",
            last_name="Dupont",
            email="alice@example.com",
        )
        learner_2 = factories.UserFactory(
            first_name="Bob",
            last_name="Martin",
            email="bob@example.com",
        )
        factories.OrderFactory(
            batch_order=batch_order,
            owner=learner_1,
            product=batch_order.offering.product,
            course=batch_order.offering.course,
            organization=batch_order.organization,
            state=enums.ORDER_STATE_COMPLETED,
        )
        factories.OrderFactory(
            batch_order=batch_order,
            owner=learner_2,
            product=batch_order.offering.product,
            course=batch_order.offering.course,
            organization=batch_order.organization,
            state=enums.ORDER_STATE_COMPLETED,
        )

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/seats-export/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="batch_order_{batch_order.id}_seats.csv"',
        )

        csv_content = response.getvalue().decode().strip().splitlines()
        self.assertEqual(len(csv_content), 3)
        self.assertEqual(csv_content[0], "Last name,First name,Email")

        rows = sorted(csv_content[1:])
        self.assertEqual(rows[0], "Dupont,Alice,alice@example.com")
        self.assertEqual(rows[1], "Martin,Bob,bob@example.com")

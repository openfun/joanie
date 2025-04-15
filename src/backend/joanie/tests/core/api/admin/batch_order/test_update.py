"""Test suite for the admin batch orders API update endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories


class BatchOrderAdminApiUpdateTestCase(TestCase):
    """Test suite for the admin batch orders API update endpoint."""

    def test_api_admin_batch_orders_update_anonymous(self):
        """Anonymous user should not be able to update a batch order."""

        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_orders_update_authenticated(self):
        """Authenticated user should not be able to partial update a batch order."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_order_update_authenticated(self):
        """
        Authenticated admin user can update a batch order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(nb_seats=2)
        batch_order.init_flow()
        new_owner = factories.UserFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
            content_type="application/json",
            data={
                "owner": str(new_owner.id),
                "company_name": "New company name",
                "trainees": [
                    {"first_name": "John", "last_name": "Doe"},
                    {"first_name": "Jane", "last_name": "Does"},
                ],
            },
        )

        batch_order.refresh_from_db()

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

    def test_api_admin_batch_orders_update_with_voucher_code(self):
        """
        Authenticated admin user should not be able to update the batch order with
        a voucher code if the state is not in `draft` or `assigned`. Else, a new total
        should be computed.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        voucher = factories.VoucherFactory(discount=factories.DiscountFactory(rate=0.1))

        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(
                    nb_seats=2, relation__product__price=100, voucher=None, state=state
                )
                if state == enums.BATCH_ORDER_STATE_DRAFT:
                    batch_order.init_flow()

                response = self.client.put(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
                    content_type="application/json",
                    data={
                        "voucher": voucher.code,
                    },
                )

                batch_order.refresh_from_db()

                if state in enums.BATCH_ORDER_STATES_MUTABLE_TOTAL:
                    self.assertEqual(
                        response.status_code, HTTPStatus.OK, response.json()
                    )
                    self.assertIsNotNone(batch_order.voucher)
                    self.assertEqual(batch_order.total, float(180.0))
                else:
                    self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
                    self.assertIsNone(batch_order.voucher)
                    self.assertEqual(
                        response.json(),
                        f"Cannot add a voucher code when batch order is in state {state}",
                    )

    def test_api_admin_batch_orders_partial_update_trainees(self):
        """
        Authenticated admin user can update the trainees of the batch order
        only if the contract is not signed already by the company.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        updated_trainees = [
            {"first_name": "John", "last_name": "Doe"},
            {"first_name": "Jane", "last_name": "Does"},
        ]

        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(
                    nb_seats=2, relation__product__price=100, state=state
                )
                response = self.client.put(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
                    content_type="application/json",
                    data={
                        "trainees": updated_trainees,
                    },
                )

                batch_order.refresh_from_db()

                if state in enums.BATCH_ORDER_STATES_ALLOWS_CONTRACT_UPDATE:
                    self.assertEqual(
                        response.status_code, HTTPStatus.OK, response.json()
                    )
                    self.assertEqual(batch_order.trainees, updated_trainees)
                else:
                    self.assertEqual(
                        response.status_code, HTTPStatus.BAD_REQUEST, response.json()
                    )
                    self.assertEqual(
                        response.json(),
                        f"Cannot update batch order in state {batch_order.state}, "
                        "contract is signed.",
                    )

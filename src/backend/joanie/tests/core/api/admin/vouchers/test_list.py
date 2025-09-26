"""Test suite for the admin vouchers API list endpoint."""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class VouchersAdminApiListTestCase(BaseAPITestCase):
    """Test suite for the admin vouchers API list endpoint."""

    maxDiff = None

    def setUp(self):
        super().setUp()
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

    def _test_vouchers_results(self, expected_vouchers=None, status=None, query=None):
        """Helper to assert that the results of a query match the expected vouchers."""
        if expected_vouchers is None:
            expected_vouchers = []

        query = f"?query={query}" if query else ""
        response = self.client.get(f"/api/v1.0/admin/vouchers/{query}")

        if status:
            self.assertStatusCodeEqual(response, status)
            return

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            len(expected_vouchers),
            content["count"],
            f"Count mismatch for query '{query}'",
        )
        self.assertCountEqual(
            [
                {
                    "id": str(voucher.id),
                    "code": voucher.code,
                    "discount": {
                        "id": str(voucher.discount.id),
                        "is_used": voucher.discount.usage_count,
                        "amount": voucher.discount.amount,
                        "rate": voucher.discount.rate,
                    },
                    "is_active": True,
                    "multiple_use": False,
                    "multiple_users": False,
                    "created_on": format_date(voucher.created_on),
                    "updated_on": format_date(voucher.updated_on),
                    "orders_count": voucher.orders.count(),
                }
                for voucher in expected_vouchers
            ],
            content["results"],
            f"Results mismatch for query '{query}'",
        )

    def test_api_admin_vouchers_list_without_authentication(self):
        """
        Anonymous users should not be able to request vouchers endpoint.
        """
        self.client.logout()
        self._test_vouchers_results(status=HTTPStatus.UNAUTHORIZED)

    def test_api_admin_vouchers_list_with_lambda_user(self):
        """
        Lambda user should not be able to request vouchers endpoint.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        self._test_vouchers_results(status=HTTPStatus.FORBIDDEN)

    def test_api_admin_vouchers_list_with_staff_user(self):
        """
        Staff user should be able to list all existing vouchers.
        """
        voucher = factories.VoucherFactory()

        self._test_vouchers_results([voucher])

    def test_api_admin_vouchers_list(self):
        """Authenticated admin user should be able to list all existing vouchers."""
        vouchers = factories.VoucherFactory.create_batch(3)

        self._test_vouchers_results(vouchers)

    def test_api_admin_vouchers_list_pagination(self):
        """Pagination should work as expected."""
        factories.VoucherFactory.create_batch(5)

        response = self.client.get("/api/v1.0/admin/vouchers/?page_size=2")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(5, content["count"])
        self.assertEqual(
            "http://testserver/api/v1.0/admin/vouchers/?page=2&page_size=2",
            content["next"],
        )
        self.assertIsNone(content["previous"])
        self.assertEqual(2, len(content["results"]))

        response = self.client.get("/api/v1.0/admin/vouchers/?page_size=2&page=2")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(5, content["count"])
        self.assertEqual(
            "http://testserver/api/v1.0/admin/vouchers/?page=3&page_size=2",
            content["next"],
        )
        self.assertEqual(
            "http://testserver/api/v1.0/admin/vouchers/?page_size=2",
            content["previous"],
        )
        self.assertEqual(2, len(content["results"]))

    def test_api_admin_vouchers_list_filtered(self):
        """
        Authenticated admin user should be able to get the list of vouchers
        filtered by code.
        """
        abc_1_a20 = factories.VoucherFactory(code="ABC_1", discount__amount=20)
        def_1_a25 = factories.VoucherFactory(code="DEF_1", discount__amount=25)
        abc_2_a60 = factories.VoucherFactory(code="ABC_2", discount__amount=60)
        abc_1_r20 = factories.VoucherFactory(code="ABC_1r", discount__rate=0.2)
        def_1_r25 = factories.VoucherFactory(code="DEF_1r", discount__rate=0.25)
        abc_2_r60 = factories.VoucherFactory(code="ABC_2r", discount__rate=0.6)

        self._test_vouchers_results(
            [abc_1_a20, def_1_a25, abc_1_r20, def_1_r25], query="1"
        )
        self._test_vouchers_results(
            [abc_1_a20, def_1_a25, abc_2_a60, abc_1_r20, def_1_r25, abc_2_r60],
            query="2",
        )
        self._test_vouchers_results([abc_1_a20, abc_1_r20], query="20")
        self._test_vouchers_results(
            [abc_1_a20, abc_2_a60, abc_1_r20, abc_2_r60], query="ABC"
        )
        self._test_vouchers_results([abc_2_a60, abc_2_r60], query="60")
        self._test_vouchers_results([abc_2_a60, abc_2_r60], query="6")

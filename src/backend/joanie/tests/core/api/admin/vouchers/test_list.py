"""Test suite for the admin vouchers API list endpoint."""

from http import HTTPStatus

from django.utils.http import urlencode

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

    def _test_vouchers_results(
        self, expected_vouchers=None, status=None, **query_parameters
    ):
        """Helper to assert that the results of a query match the expected vouchers."""
        if expected_vouchers is None:
            expected_vouchers = []

        query_parameters = urlencode(query_parameters)

        response = self.client.get(f"/api/v1.0/admin/vouchers/?{query_parameters}")

        if status:
            self.assertStatusCodeEqual(response, status)
            return

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(
            {
                "count": len(expected_vouchers),
                "next": None,
                "previous": None,
                "results": [
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
            },
            response.json(),
            f"Response mismatch for query '{query_parameters}'",
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
        vouchers.reverse()

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
            [def_1_r25, abc_1_r20, def_1_a25, abc_1_a20], query="1"
        )
        self._test_vouchers_results(
            [abc_2_r60, def_1_r25, abc_1_r20, abc_2_a60, def_1_a25, abc_1_a20],
            query="2",
        )
        self._test_vouchers_results([abc_1_r20, abc_1_a20], query="20")
        self._test_vouchers_results(
            [abc_2_r60, abc_1_r20, abc_2_a60, abc_1_a20], query="ABC"
        )
        self._test_vouchers_results([abc_2_r60, abc_2_a60], query="60")
        self._test_vouchers_results([abc_2_r60, abc_2_a60], query="6")
        self._test_vouchers_results([abc_2_r60, def_1_r25, abc_1_r20], query="r")

    def test_api_admin_vouchers_list_ordered(self):
        """
        Authenticated admin user should be able to get the list of vouchers
        ordered an attribute.
        """
        abc_1 = factories.VoucherFactory(code="ABC_1", discount__amount=20)
        def_1 = factories.VoucherFactory(code="DEF_1", discount__amount=25)
        abc_2 = factories.VoucherFactory(code="ABC_2", discount__amount=60)
        abc_1r = factories.VoucherFactory(code="ABC_1r", discount__rate=0.2)
        def_1r = factories.VoucherFactory(code="DEF_1r", discount__rate=0.25)
        abc_2r = factories.VoucherFactory(code="ABC_2r", discount__rate=0.6)

        self._test_vouchers_results(
            [abc_1, def_1, abc_2, abc_1r, def_1r, abc_2r], ordering="created_on"
        )
        self._test_vouchers_results(
            [abc_2r, def_1r, abc_1r, abc_2, def_1, abc_1], ordering="-created_on"
        )

        self._test_vouchers_results(
            [abc_1, abc_1r, abc_2, abc_2r, def_1, def_1r], ordering="code"
        )
        self._test_vouchers_results(
            [def_1r, def_1, abc_2r, abc_2, abc_1r, abc_1], ordering="-code"
        )

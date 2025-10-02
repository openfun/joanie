"""Tests for the Order create with voucher API."""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.payment.factories import BillingAddressDictFactory
from joanie.tests.base import BaseAPITestCase


class OrderCreateVoucherApiTest(BaseAPITestCase):
    """Test the API of the Order create with voucher endpoint."""

    maxDiff = None

    def create_order(self, voucher, user=None, offering=None):
        """Make a POST request to the endpoint."""
        if not user:
            user = factories.UserFactory()

        if not offering:
            offering = factories.OfferingFactory()

        data = {
            "course_code": offering.course.code,
            "organization_id": str(offering.organizations.first().id),
            "product_id": str(offering.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
            "voucher_code": voucher.code,
        }

        token = self.generate_token_from_user(user)
        return self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_api_order_create_voucher(self):
        """
        Authenticated user wants to create an order with a voucher discount.
        """
        offering = factories.OfferingFactory(
            product__price=100,
        )
        voucher = factories.VoucherFactory(
            discount=factories.DiscountFactory(rate=0.1),
            multiple_use=False,
            multiple_users=False,
        )

        response = self.create_order(voucher, offering=offering)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        order = models.Order.objects.get()
        self.assertEqual(order.total, 90)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable_by(order.owner))

    def test_api_order_create_voucher_single_use_single_user(self):
        """
        A single use and single user voucher can be used only once.
        """
        voucher = factories.VoucherFactory(multiple_use=False, multiple_users=False)
        user_1 = factories.UserFactory()

        response = self.create_order(voucher, user=user_1)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable_by(order.owner))

        response = self.create_order(voucher, user=user_1)

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

        user_2 = factories.UserFactory(first_name="Jane", last_name="Doe")
        response = self.create_order(voucher, user=user_2)

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_order_create_voucher_multiple_use_single_user(self):
        """
        A multiple use and single user voucher can be used multiple times by the same user.
        """
        voucher = factories.VoucherFactory(
            multiple_use=True,
            multiple_users=False,
            discount=factories.DiscountFactory(rate=0.1),
        )
        user_1 = factories.UserFactory()
        offering_1 = factories.OfferingFactory()

        response = self.create_order(voucher, user=user_1, offering=offering_1)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        offering_2 = factories.OfferingFactory()

        response = self.create_order(voucher, user=user_1, offering=offering_2)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        user_2 = factories.UserFactory()
        response = self.create_order(voucher, user=user_2, offering=offering_1)

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_order_create_voucher_single_use_multiple_user(self):
        """
        A single use and multiple user voucher can be used once by each user.
        """
        voucher = factories.VoucherFactory(
            multiple_use=False,
            multiple_users=True,
            discount=factories.DiscountFactory(rate=0.1),
        )
        user_1 = factories.UserFactory()
        offering_1 = factories.OfferingFactory()

        response = self.create_order(voucher, user=user_1, offering=offering_1)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable_by(order.owner))

        offering_2 = factories.OfferingFactory()

        response = self.create_order(voucher, user=user_1, offering=offering_2)

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

        user_2 = factories.UserFactory()
        response = self.create_order(voucher, user=user_2, offering=offering_1)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable_by(order.owner))

    def test_api_order_create_voucher_multiple_use_multiple_user(self):
        """
        A multiple use and multiple user voucher can be used multiple times by
        each user.
        """
        voucher = factories.VoucherFactory(
            multiple_use=True,
            multiple_users=True,
            discount=factories.DiscountFactory(rate=0.1),
        )
        user_1 = factories.UserFactory()
        offering_1 = factories.OfferingFactory()

        response = self.create_order(voucher, user=user_1, offering=offering_1)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        offering_2 = factories.OfferingFactory()

        response = self.create_order(voucher, user=user_1, offering=offering_2)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        user_2 = factories.UserFactory()
        response = self.create_order(voucher, user=user_2, offering=offering_1)

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

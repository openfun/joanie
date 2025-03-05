"""Tests for the Order create with voucher API."""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.payment.factories import BillingAddressDictFactory
from joanie.tests.base import BaseAPITestCase


class OrderCreateVoucherApiTest(BaseAPITestCase):
    """Test the API of the Order create with voucher endpoint."""

    maxDiff = None

    def create_order(self, voucher, user=None, relation=None):
        """Make a POST request to the endpoint."""
        if not user:
            user = factories.UserFactory()

        if not relation:
            relation = voucher.order_group.course_product_relation

        data = {
            "course_code": relation.course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(relation.product.id),
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
        voucher = factories.VoucherFactory(
            order_group__discount=factories.DiscountFactory(rate=0.1),
            order_group__course_product_relation__product__price=100,
            order_group__nb_seats=None,
            multiple_use=False,
            multiple_users=False,
        )

        response = self.create_order(voucher)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

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

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable_by(order.owner))

        response = self.create_order(voucher, user=user_1)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

        user_2 = factories.UserFactory(first_name="Jane", last_name="Doe")
        response = self.create_order(voucher, user=user_2)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_order_create_voucher_multiple_use_single_user(self):
        """
        A multiple use and single user voucher can be used multiple times by the same user.
        """
        voucher = factories.VoucherFactory(
            order_group=None,
            multiple_use=True,
            multiple_users=False,
            discount=factories.DiscountFactory(rate=0.1),
        )
        user_1 = factories.UserFactory()
        relation_1 = factories.CourseProductRelationFactory()

        response = self.create_order(voucher, user=user_1, relation=relation_1)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        relation_2 = factories.CourseProductRelationFactory()

        response = self.create_order(voucher, user=user_1, relation=relation_2)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        user_2 = factories.UserFactory()
        response = self.create_order(voucher, user=user_2, relation=relation_1)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

    def test_api_order_create_voucher_single_use_multiple_user(self):
        """
        A single use and multiple user voucher can be used once by each user.
        """
        voucher = factories.VoucherFactory(
            order_group=None,
            multiple_use=False,
            multiple_users=True,
            discount=factories.DiscountFactory(rate=0.1),
        )
        user_1 = factories.UserFactory()
        relation_1 = factories.CourseProductRelationFactory()

        response = self.create_order(voucher, user=user_1, relation=relation_1)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable_by(order.owner))

        relation_2 = factories.CourseProductRelationFactory()

        response = self.create_order(voucher, user=user_1, relation=relation_2)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())

        user_2 = factories.UserFactory()
        response = self.create_order(voucher, user=user_2, relation=relation_1)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
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
            order_group=None,
            multiple_use=True,
            multiple_users=True,
            discount=factories.DiscountFactory(rate=0.1),
        )
        user_1 = factories.UserFactory()
        relation_1 = factories.CourseProductRelationFactory()

        response = self.create_order(voucher, user=user_1, relation=relation_1)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        relation_2 = factories.CourseProductRelationFactory()

        response = self.create_order(voucher, user=user_1, relation=relation_2)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

        user_2 = factories.UserFactory()
        response = self.create_order(voucher, user=user_2, relation=relation_1)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())
        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertTrue(voucher.is_usable_by(order.owner))

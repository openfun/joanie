"""Test suite for the admin orders API create endpoint."""

from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class OrdersAdminApiCreateTestCase(BaseAPITestCase):
    """Test suite for the admin orders API create endpoint."""

    maxDiff = None

    def test_api_admin_orders_create_anonymous(self):
        """An anonymous user should not be able to create an order."""
        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "organization_id": str(offering.organizations.first().id),
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_orders_create_lambda_user(self):
        """A non-admin user should not be able to create an order."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "organization_id": str(offering.organizations.first().id),
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_create_staff_user(self):
        """A staff user without superuser rights should not be able to create an order."""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "organization_id": str(offering.organizations.first().id),
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_create_missing_product_id(self):
        """Creating an order without product_id should return 400."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "course_code": offering.course.code,
                "organization_id": str(offering.organizations.first().id),
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertIn("product_id", response.json())

    def test_api_admin_orders_create(self):
        """An admin user should be able to create a to_own order with a 100% voucher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        organization = offering.organizations.first()

        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "organization_id": str(organization.id),
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        data = response.json()

        # Order should exist in the database
        order = models.Order.objects.get(id=data["id"])
        self.assertEqual(order.state, enums.ORDER_STATE_TO_OWN)
        self.assertIsNone(order.owner)

        # A 100% voucher should be attached
        self.assertIsNotNone(order.voucher)
        self.assertEqual(order.voucher.discount.rate, 1)
        self.assertFalse(order.voucher.multiple_use)
        self.assertFalse(order.voucher.multiple_users)

    def test_api_admin_orders_create_with_discount_rate(self):
        """An admin should be able to create an order with a custom rate discount."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        organization = offering.organizations.first()

        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "organization_id": str(organization.id),
                "discount_type": "rate",
                "discount_value": 50,
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json()["id"])
        self.assertEqual(order.state, enums.ORDER_STATE_TO_OWN)
        self.assertIsNotNone(order.voucher)
        self.assertEqual(order.voucher.discount.rate, 0.5)
        self.assertIsNone(order.voucher.discount.amount)

    def test_api_admin_orders_create_with_discount_amount(self):
        """An admin should be able to create an order with a fixed amount discount."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        organization = offering.organizations.first()

        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "organization_id": str(organization.id),
                "discount_type": "amount",
                "discount_value": 150,
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        order = models.Order.objects.get(id=response.json()["id"])
        self.assertEqual(order.state, enums.ORDER_STATE_TO_OWN)
        self.assertIsNotNone(order.voucher)
        self.assertIsNone(order.voucher.discount.rate)
        self.assertEqual(order.voucher.discount.amount, 150)

    def test_api_admin_orders_create_with_discount_rate_over_100(self):
        """A rate discount value above 100 should be rejected."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "discount_type": "rate",
                "discount_value": 150,
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertIn("discount_value", response.json())

    def test_api_admin_orders_create_with_discount_rate_zero(self):
        """A rate discount value of 0 should be rejected."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "discount_type": "rate",
                "discount_value": 0,
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertIn("discount_value", response.json())

    def test_api_admin_orders_create_with_discount_amount_decimal(self):
        """A non-integer amount discount should be rejected."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "discount_type": "amount",
                "discount_value": 10.5,
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertIn("discount_value", response.json())

    def test_api_admin_orders_create_with_discount_amount_negative(self):
        """A negative amount discount should be rejected."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "discount_type": "amount",
                "discount_value": -10,
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertIn("discount_value", response.json())

    def test_api_admin_orders_create_with_discount_type_without_value(self):
        """Providing discount_type without discount_value should be rejected."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering = factories.OfferingFactory()
        response = self.client.post(
            "/api/v1.0/admin/orders/",
            data={
                "product_id": str(offering.product.id),
                "course_code": offering.course.code,
                "discount_type": "rate",
            },
            content_type="application/json",
        )
        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

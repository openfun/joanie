"""Tests for the Order submit API."""

from http import HTTPStatus

from django.core.cache import cache

from joanie.core import enums, factories
from joanie.payment.factories import BillingAddressDictFactory
from joanie.tests.base import BaseAPITestCase


class OrderSubmitApiTest(BaseAPITestCase):
    """Test the API of the Order submit endpoint."""

    maxDiff = None

    def _get_fee_order(self, **kwargs):
        """Return a fee order linked to a course."""
        return factories.OrderFactory(**kwargs)

    def _get_fee_enrollment_order(self, **kwargs):
        """Return a fee order linked to an enrollment."""
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CERTIFICATE
        )
        enrollment = factories.EnrollmentFactory(
            user=kwargs["owner"], course_run__course=relation.course
        )

        return factories.OrderFactory(
            **kwargs,
            course=None,
            enrollment=enrollment,
            product=relation.product,
        )

    def _get_free_order(self, **kwargs):
        """Return a free order."""
        product = factories.ProductFactory(price=0.00)

        return factories.OrderFactory(**kwargs, product=product)

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_submit_anonymous(self):
        """
        Anonymous user cannot submit order
        """
        order = factories.OrderFactory()
        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_unexisting(self):
        """
        User should receive 404 when submitting a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.patch(
            "/api/v1.0/orders/notarealid/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_order_submit_authenticated_not_owned(self):
        """
        Authenticated user should not be able to submit order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"billing_address": BillingAddressDictFactory()},
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_no_billing_address(self):
        """
        User should not be able to submit a fee order without billing address
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(owner=user)

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"billing_address": ["This field is required."]}
        )
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_success(self):
        """
        User should be able to submit a fee order with a billing address
        or a free order without a billing address
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        orders = [
            self._get_free_order(owner=user),
            self._get_fee_order(owner=user),
            self._get_fee_enrollment_order(owner=user),
        ]

        for order in orders:
            # Submitting the fee order
            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/submit/",
                content_type="application/json",
                data={"billing_address": BillingAddressDictFactory()},
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            order.refresh_from_db()
            self.assertEqual(response.status_code, HTTPStatus.CREATED)
            # Order should have been automatically validated if it is free
            # Otherwise it should have been submitted
            self.assertEqual(
                order.state,
                enums.ORDER_STATE_SUBMITTED
                if order.total > 0
                else enums.ORDER_STATE_VALIDATED,
            )

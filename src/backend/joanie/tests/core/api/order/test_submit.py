"""Tests for the Order submit API."""

from http import HTTPStatus
from unittest import mock

from django.core.cache import cache

from joanie.core import enums, factories
from joanie.core.api.client import OrderViewSet
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

    def test_api_order_submit_should_auto_assign_organization(self):
        """
        On submit request, if the related order has no organization linked yet, the one
        implied in the course product organization with the least order should be
        assigned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        orders = [
            self._get_free_order(owner=user, organization=None),
            self._get_fee_order(owner=user, organization=None),
            self._get_fee_enrollment_order(owner=user, organization=None),
        ]

        for order in orders:
            # Order should have no organization set yet
            self.assertIsNone(order.organization)

            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/submit/",
                content_type="application/json",
                data={"billing_address": BillingAddressDictFactory()},
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            order.refresh_from_db()
            self.assertEqual(response.status_code, HTTPStatus.CREATED)
            # Now order should have an organization set
            self.assertIsNotNone(order.organization)

    @mock.patch.object(
        OrderViewSet, "_get_organization_with_least_active_orders", return_value=None
    )
    def test_api_order_submit_should_auto_assign_organization_if_needed(
        self, mocked_round_robin
    ):
        """
        Order should have organization auto assigned only on submit if it has
        not already one linked.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Auto assignment should have been triggered if order has no organization linked
        order = factories.OrderFactory(owner=user, organization=None)
        self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            data={"billing_address": BillingAddressDictFactory()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mocked_round_robin.assert_called_once()

        mocked_round_robin.reset_mock()

        # Auto assignment should not have been
        # triggered if order already has an organization linked
        order = factories.OrderFactory(owner=user)
        self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            data={"billing_address": BillingAddressDictFactory()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mocked_round_robin.assert_not_called()

    @mock.patch.object(
        OrderViewSet, "_get_organization_with_least_active_orders", return_value=None
    )
    def test_api_order_submit_should_auto_assign_organization_if_pending(
        self, mocked_round_robin
    ):
        """
        Order should have organization auto assigned on submit if its state is
        pending
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Auto assignment should have been triggered if order has no organization linked
        order = factories.OrderFactory(owner=user, state=enums.ORDER_STATE_PENDING)
        self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            data={"billing_address": BillingAddressDictFactory()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mocked_round_robin.assert_called_once()

    def test_api_order_submit_auto_assign_organization_with_least_orders(self):
        """
        Order auto-assignment logic should always return the organization with the least
        active orders count for the given product course relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )

        relation = factories.CourseProductRelationFactory(
            organizations=[organization, expected_organization]
        )

        # Create 3 orders for the first organization (1 draft, 1 pending, 1 canceled)
        factories.OrderFactory(
            organization=organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_DRAFT,
        )
        factories.OrderFactory(
            organization=organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_PENDING,
        )
        factories.OrderFactory(
            organization=organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_CANCELED,
        )

        # 2 ignored orders for the second organization (1 pending, 1 canceled)
        factories.OrderFactory(
            organization=expected_organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_PENDING,
        )
        factories.OrderFactory(
            organization=expected_organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_CANCELED,
        )

        # Then create an order without organization
        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            organization=None,
        )

        # Submit it should auto assign organization with least active orders
        self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            data={"billing_address": BillingAddressDictFactory()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()
        self.assertEqual(order.organization, expected_organization)

    def test_api_order_submit_get_organization_with_least_active_orders_prefer_author(
        self,
    ):
        """
        In case of order count equality, the method _get_organization_with_least_orders should
        return first organization which is also an author of the course.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization, expected_organization = (
            factories.OrganizationFactory.create_batch(2)
        )

        relation = factories.CourseProductRelationFactory(
            organizations=[organization, expected_organization]
        )

        relation.course.organizations.set([expected_organization])

        # Create 3 orders for the first organization (1 draft, 1 pending, 1 canceled)
        factories.OrderFactory(
            organization=organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_PENDING,
        )
        factories.OrderFactory(
            organization=organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_CANCELED,
        )

        # 2 ignored orders for the second organization (1 pending, 1 canceled)
        factories.OrderFactory(
            organization=expected_organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_PENDING,
        )
        factories.OrderFactory(
            organization=expected_organization,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_CANCELED,
        )

        # Then create an order without organization
        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            organization=None,
        )

        self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            data={"billing_address": BillingAddressDictFactory()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()

        self.assertEqual(order.organization, expected_organization)

"""Tests for the Order update API."""

import json
import random
import uuid
from http import HTTPStatus

from django.core.cache import cache

from joanie.core import enums, factories, models
from joanie.payment.models import Invoice, Transaction
from joanie.tests.base import BaseAPITestCase


class OrderUpdateApiTest(BaseAPITestCase):
    """Test the API of the Order update endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    # pylint: disable=too-many-locals
    def _check_api_order_update_detail(self, order, user, error_code):
        """Nobody should be allowed to update an order."""
        owner_token = self.generate_token_from_user(order.owner)

        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {owner_token}",
        )
        data = json.loads(response.content)

        # Get data for another product we will use as alternative values
        # to try to modify our order
        other_owner = factories.UserFactory(is_superuser=random.choice([True, False]))
        *other_target_courses, _other_course = factories.CourseFactory.create_batch(3)
        other_product = factories.ProductFactory(target_courses=other_target_courses)
        other_order = factories.OrderFactory(owner=other_owner, product=other_product)
        other_owner_token = self.generate_token_from_user(other_owner)

        other_response = self.client.get(
            f"/api/v1.0/orders/{other_order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {other_owner_token}",
        )
        other_data = json.loads(other_response.content)
        other_data["id"] = uuid.uuid4()

        # Try modifying the order on each field with our alternative data
        self.assertListEqual(
            list(data.keys()),
            [
                "certificate_id",
                "contract",
                "course",
                "created_on",
                "enrollment",
                "id",
                "main_invoice_reference",
                "order_group_id",
                "organization",
                "owner",
                "product_id",
                "state",
                "target_courses",
                "target_enrollments",
                "total",
                "total_currency",
                "payment_schedule",
            ],
        )
        headers = (
            {"HTTP_AUTHORIZATION": f"Bearer {self.generate_token_from_user(user)}"}
            if user
            else {}
        )
        for field in data:
            initial_value = data[field]

            # With full object
            data[field] = other_data[field]
            response = self.client.put(
                f"/api/v1.0/orders/{order.id}/",
                data=data,
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # With partial object
            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/",
                data={field: other_data[field]},
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # Check that nothing was modified
            self.assertEqual(models.Order.objects.count(), 2)
            response = self.client.get(
                f"/api/v1.0/orders/{order.id}/",
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {owner_token}",
            )
            new_data = json.loads(response.content)
            self.assertEqual(new_data[field], initial_value)

    def test_api_order_update_detail_anonymous(self):
        """An anonymous user should not be allowed to update any order."""
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, None, HTTPStatus.UNAUTHORIZED)

    def test_api_order_update_detail_authenticated_superuser(self):
        """An authenticated superuser should not be allowed to update any order."""
        user = factories.UserFactory(is_superuser=True, is_staff=True)
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, user, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_order_update_detail_authenticated_unowned(self):
        """
        An authenticated user should not be allowed to update an order
        they do not own.
        """
        user = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, user, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_order_update_detail_authenticated_owned(self):
        """
        An authenticated user should not be allowed to update an order
        they own, no matter the state.
        """
        owner = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_SUBMITTED
        )
        self._check_api_order_update_detail(order, owner, HTTPStatus.METHOD_NOT_ALLOWED)
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_VALIDATED
        )
        self._check_api_order_update_detail(order, owner, HTTPStatus.METHOD_NOT_ALLOWED)
        Transaction.objects.all().delete()
        Invoice.objects.all().delete()
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_PENDING
        )
        self._check_api_order_update_detail(order, owner, HTTPStatus.METHOD_NOT_ALLOWED)
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_CANCELED
        )
        self._check_api_order_update_detail(order, owner, HTTPStatus.METHOD_NOT_ALLOWED)
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_DRAFT
        )
        self._check_api_order_update_detail(order, owner, HTTPStatus.METHOD_NOT_ALLOWED)

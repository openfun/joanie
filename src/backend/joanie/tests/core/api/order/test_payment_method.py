"""Tests for the Order payment method API."""

from http import HTTPStatus

from joanie.core import enums, factories
from joanie.payment.factories import CreditCardFactory
from joanie.tests.base import BaseAPITestCase


class OrderPaymentMethodApiTest(BaseAPITestCase):
    """Test the API of the Order payment method endpoint."""

    def test_order_payment_method_anoymous(self):
        """
        Anonymous users should not be able to set a payment method on an order.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            credit_card=None,
        )
        self.assertFalse(order.has_payment_method)

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/payment-method/",
            data={"credit_card_id": "1"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)
        self.assertIsNone(order.credit_card)
        self.assertFalse(order.has_payment_method)

    def test_order_payment_method_user_is_not_order_owner(self):
        """
        Authenticated users should not be able to set a payment method on an order
        if they are not the owner of the order.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            credit_card=None,
        )
        self.assertFalse(order.has_payment_method)

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/payment-method/",
            data={"credit_card_id": "1"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)
        self.assertIsNone(order.credit_card)
        self.assertFalse(order.has_payment_method)

    def test_order_payment_method_no_credit_card(self):
        """
        Authenticated users should not be able to set a payment method on an order
        if they do not provide a credit card id.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            credit_card=None,
        )
        self.assertFalse(order.has_payment_method)

        token = self.generate_token_from_user(order.owner)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/payment-method/",
            data={},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"credit_card_id":"This field is required."}',
            status_code=HTTPStatus.BAD_REQUEST,
        )
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)
        self.assertIsNone(order.credit_card)
        self.assertFalse(order.has_payment_method)

    def test_order_payment_method_user_is_not_credit_card_owner(self):
        """
        Authenticated users should not be able to set a payment method on an order
        if they are not the owner of the credit card.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            credit_card=None,
        )
        self.assertFalse(order.has_payment_method)

        credit_card = CreditCardFactory()
        token = self.generate_token_from_user(order.owner)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/payment-method/",
            data={"credit_card_id": str(credit_card.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response, "Credit card does not exist.", status_code=HTTPStatus.NOT_FOUND
        )
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)
        self.assertIsNone(order.credit_card)
        self.assertFalse(order.has_payment_method)

    def test_order_payment_method_authenticated(self):
        """
        Authenticated users should be able to set a payment method on an order
        by providing a credit card id.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            credit_card=None,
        )
        self.assertFalse(order.has_payment_method)

        credit_card = CreditCardFactory(owner=order.owner)
        token = self.generate_token_from_user(order.owner)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/payment-method/",
            data={"credit_card_id": str(credit_card.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
        self.assertEqual(order.credit_card, credit_card)
        self.assertTrue(order.has_payment_method)

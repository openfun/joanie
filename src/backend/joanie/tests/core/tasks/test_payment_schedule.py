"""
Test suite for payment schedule tasks
"""

from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase

from joanie.core.enums import (
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import OrderFactory
from joanie.core.tasks.payment_schedule import process_today_installment
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.factories import CreditCardFactory
from joanie.tests.base import BaseLogMixinTestCase


class PaymentScheduleTasksTestCase(TestCase, BaseLogMixinTestCase):
    """
    Test suite for payment schedule tasks
    """

    maxDiff = None

    @mock.patch.object(
        DummyPaymentBackend,
        "create_zero_click_payment",
        side_effect=DummyPaymentBackend().create_zero_click_payment,
    )
    def test_utils_payment_schedule_process_today_installment_succeeded(
        self, mock_create_zero_click_payment
    ):
        """Check today's installment is processed"""
        credit_card = CreditCardFactory()
        order = OrderFactory(
            id="6134df5e-a7eb-4cb3-aceb-d0abfe330af6",
            state=ORDER_STATE_PENDING,
            owner=credit_card.owner,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            process_today_installment.run(order.id)

        mock_create_zero_click_payment.assert_called_once_with(
            order=order,
            credit_card_token=credit_card.token,
            installment={
                "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                "amount": "200.00",
                "due_date": "2024-01-17",
                "state": PAYMENT_STATE_PENDING,
            },
        )

    def test_utils_payment_schedule_process_today_installment_no_card(self):
        """Check today's installment is processed"""
        order = OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            process_today_installment.run(order.id)

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_NO_PAYMENT)

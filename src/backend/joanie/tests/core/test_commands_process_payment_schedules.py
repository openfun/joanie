"""Tests for the `process_payment_schedules` management command."""

from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase

from joanie.core import factories
from joanie.core.enums import (
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
)


class ProcessPaymentSchedulesTestCase(TestCase):
    """Test case for the management command `process_payment_schedules`."""

    def test_commands_process_payment_schedules(self):
        """
        This command should process all pending payment schedules.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-18",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-18",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-18",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-18",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        mocked_now = datetime(2024, 2, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with (
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
            mock.patch(
                "joanie.core.tasks.payment_schedule.process_today_installment"
            ) as process_today_installment,
        ):
            call_command("process_payment_schedules")

        process_today_installment.delay.assert_called_once_with(order.id)

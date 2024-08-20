"""Tests for the `send_mail_upcoming_debit` management command"""

from datetime import date
from decimal import Decimal as D
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from joanie.core import enums, factories


@override_settings(
    JOANIE_PAYMENT_SCHEDULE_LIMITS={1000: (20, 30, 30, 20)},
    JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS=2,
    DEFAULT_CURRENCY="EUR",
)
class SendMailUpcomingDebitManagementCommandTestCase(TestCase):
    """Test case for the management command `send_mail_upcoming_debit`"""

    @override_settings(JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS=2)
    def test_command_send_mail_upcoming_debit_with_installment_reminder_period_of_2_days(
        self,
    ):
        """
        According to the value configured in the setting `JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS`,
        that is 2 days for this test, the command should find the 2nd installment that will
        be debited next and call the task that is responsible to send an email to the order's
        owner. The task must be called with the `order.id` and the installment id
        that is concerned in the order payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            product__price=D("1000.00"),
            product__title="Product 1",
        )
        order.payment_schedule[0]["state"] = enums.PAYMENT_STATE_PAID
        order.payment_schedule[0]["due_date"] = date(2024, 1, 17)
        order.payment_schedule[1]["id"] = "1932fbc5-d971-48aa-8fee-6d637c3154a5"
        order.payment_schedule[1]["state"] = enums.PAYMENT_STATE_PENDING
        order.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order.save()

        order_2 = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            product__price=D("1000.00"),
            product__title="Product 2",
        )
        order_2.payment_schedule[0]["state"] = enums.PAYMENT_STATE_PAID
        order_2.payment_schedule[1]["due_date"] = date(2024, 2, 18)
        order_2.payment_schedule[1]["state"] = enums.PAYMENT_STATE_PENDING
        order_2.save()

        with (
            mock.patch(
                "django.utils.timezone.localdate", return_value=date(2024, 2, 15)
            ),
            mock.patch(
                "joanie.core.management.commands.send_mail_upcoming_debit"
                ".send_mail_reminder_installment_debit_task"
            ) as send_mail_reminder_installment_debit_task,
        ):
            call_command("send_mail_upcoming_debit")

        send_mail_reminder_installment_debit_task.delay.assert_called_once_with(
            order_id=order.id, installment_id="1932fbc5-d971-48aa-8fee-6d637c3154a5"
        )
